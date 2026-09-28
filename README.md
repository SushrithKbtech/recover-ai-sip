# RecoverAI

A personal-finance "what would happen if" simulator. Describe a financial decision in
plain language and RecoverAI extracts the parameters, runs deterministic calculators,
and explains the trade-offs side by side.

**Core design principle:** the LLM never does arithmetic. It only (1) extracts structured
parameters from your message, (2) decides which calculator applies, (3) asks a clarifying
question if something's missing, and (4) explains the calculator's output in plain
language. All numbers come from `backend/app/calculators.py`, a pure-Python module with
zero LLM/API calls — verify this yourself with:

```bash
grep -iE "openai|anthropic|langchain|requests|httpx" backend/app/calculators.py
# (no output = confirmed clean)
```

## Architecture

Orchestration is a real LangGraph `StateGraph` with conditional edges — not a linear
function chain or a pile of if-statements.

```mermaid
flowchart TD
    START([START]) --> intent_parser

    intent_parser{{"intent_parser (LLM)\nstructured extraction + scenario routing"}}
    clarify["clarify (LLM)\ngenerate clarifying question"]
    calculator_dispatch["calculator_dispatch (pure Python)\nNO LLM CALL"]
    explainer["explainer (LLM)\ngrounded in calculator output only"]
    out_of_scope["out_of_scope\nexplain what RecoverAI can/can't do"]

    intent_parser -- "required fields missing/ambiguous" --> clarify
    intent_parser -- "all required fields present" --> calculator_dispatch
    intent_parser -- "not one of the 3 scenarios" --> out_of_scope

    calculator_dispatch -- "validation succeeded" --> explainer
    calculator_dispatch -- "validation failed" --> clarify

    clarify --> END1([END\nawait user reply, loop back to intent_parser on next turn])
    explainer --> END2([END])
    out_of_scope --> END3([END])
```

Because `/api/chat` is a stateless request/response endpoint, the `clarify -> intent_parser`
loop happens *across* HTTP calls: each session's transcript is persisted in MySQL keyed by
`session_id`, and every new user message re-invokes the graph from `intent_parser` with the
full accumulated conversation. Because state lives in the database rather than in process
memory, a session survives a backend restart and can be resumed by any instance, so the API
can be scaled horizontally.

### Nodes

| Node | LLM call? | Responsibility |
|---|---|---|
| `intent_parser` | Yes (structured/JSON-mode) | Picks which of the 3 calculator scenarios applies, extracts parameters, flags missing fields |
| `clarify` | Yes | Writes one natural-language question asking for exactly what's missing |
| `calculator_dispatch` | **No** | Pure Python — validates inputs, calls the matching calculator function |
| `explainer` | Yes | Turns calculator output into a plain-language summary; system prompt forbids inventing numbers |
| `out_of_scope` | No | Returns a fixed explanation of what RecoverAI can and can't do |

## Persistence (MySQL)

Conversation state, transcripts, and every completed calculation are stored in MySQL via
SQLAlchemy. The graph itself stays storage-agnostic: it takes a state dict and returns one,
and `app/repository.py` is the only module that knows about rows.

### Schema

| Table | Purpose | Key columns |
|---|---|---|
| `chat_sessions` | One row per conversation; holds the durable slice of graph state | `id` (PK, session id), `scenario`, `params` (JSON), `missing_fields` (JSON), `awaiting_clarification`, `created_at`, `updated_at` |
| `messages` | Full transcript, replayed into the graph each turn | `id` (PK), `session_id` (FK, cascade), `role`, `content`, `created_at` |
| `computations` | Every completed calculator run, for history and analytics | `id` (PK), `session_id` (FK, cascade), `scenario`, `params` (JSON), `result` (JSON), `created_at` |

Both child tables cascade on delete, so removing a session removes its transcript and
calculation history in one statement.

### Indexing and connection handling

- `ix_messages_session_id_id` is a composite on `(session_id, id)`. Every turn re-reads one
  session's entire transcript in insertion order, which is the hot read path, and the
  composite lets that run as a single range scan instead of a filter plus sort.
- `ix_computations_scenario_created_at` covers the scenario analytics aggregate behind
  `/api/stats`.
- `chat_sessions.updated_at` is indexed so stale sessions can be swept by age.
- The engine sets `pool_recycle=3600`, below MySQL's default 8 hour `wait_timeout`, so
  connections idle long enough to be dropped server side are replaced before reuse rather
  than failing mid request with "MySQL server has gone away". `pool_pre_ping` catches the
  rest.
- `/api/chat` deliberately does **not** hold a connection across the LLM calls. It opens a
  short transaction to load state, closes it, runs the graph, then opens a second short
  transaction to write the turn. Holding a pooled connection across multi-second model
  latency would exhaust the pool under concurrency.
- The connection string uses `utf8mb4`, which is required here: amounts are rendered with
  the rupee sign, and MySQL's legacy 3 byte `utf8` cannot store it.

The driver is PyMySQL, which is pure Python, so the Docker image needs no MySQL client
system libraries.

## Project layout

```
recoverai/
  docker-compose.yml     # local MySQL 8 for development
  backend/
    app/
      calculators.py   # pure, deterministic, unit-testable math (no LLM)
      graph.py          # LangGraph StateGraph + nodes + conditional edges
      schemas.py        # Pydantic models: API I/O + structured LLM output
      db.py             # SQLAlchemy engine, pooling config, session factory
      models.py         # ORM models: chat_sessions, messages, computations
      repository.py     # state <-> rows, transcript reads, scenario analytics
      main.py            # FastAPI app, routes
    tests/
      test_calculators.py
      test_repository.py   # integration tests against a real MySQL
    requirements.txt
    Dockerfile
    render.yaml
    .env.example
  frontend/
    src/
      App.tsx
      api.ts
      types.ts
      components/
        Chat.tsx
        ResultView.tsx
    vercel.json
    .env.example
```

## Setup — database

Start a local MySQL 8 with Docker:

```bash
docker compose up -d mysql
```

Or, against an existing MySQL server, create the database and user once:

```sql
CREATE DATABASE recoverai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'recoverai'@'localhost' IDENTIFIED BY 'recoverai';
GRANT ALL PRIVILEGES ON recoverai.* TO 'recoverai'@'localhost';
FLUSH PRIVILEGES;
```

Tables are created automatically on backend startup.

## Setup — backend

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate   # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env       # then fill in OPENAI_API_KEY and DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

Run the calculator unit tests (no API key or database needed — this module has no LLM calls):

```bash
pytest tests/test_calculators.py -q
```

Run everything including the MySQL integration tests (these skip automatically if
`DATABASE_URL` is unreachable):

```bash
pytest tests/ -q
```

## Setup — frontend

```bash
cd frontend
npm install
cp .env.example .env   # set VITE_API_BASE_URL if backend isn't on localhost:8000
npm run dev
```

Open `http://localhost:5173`.

## API contract

`POST /api/chat`

```json
// request
{ "session_id": "uuid-string", "message": "user's natural language input" }
```

```json
// response
{
  "session_id": "uuid-string",
  "type": "clarifying_question" | "result" | "error",
  "message": "agent's text response (question or lead-in to result)",
  "result": {
    "scenario": "sip_pause_vs_loan_payoff",
    "calculator_output": { "...": "raw numbers" },
    "explanation": "plain language text",
    "assumptions": ["...", "..."]
  }
}
```

If `type` is `"clarifying_question"`, `result` is `null` — POST again with the same
`session_id` and the user's answer to continue the conversation.

`GET /api/sessions/{session_id}/history`

Returns the stored transcript and every calculation run in that session. `404` if the
session id has never been seen.

```json
{
  "session_id": "uuid-string",
  "scenario": "opportunity_cost",
  "awaiting_clarification": false,
  "created_at": "2026-09-28T10:14:02",
  "updated_at": "2026-09-28T10:15:47",
  "messages": [
    { "role": "user", "content": "...", "created_at": "2026-09-28T10:14:02" },
    { "role": "assistant", "content": "...", "created_at": "2026-09-28T10:14:09" }
  ],
  "computations": [
    {
      "scenario": "opportunity_cost",
      "params": { "...": "extracted inputs" },
      "result": { "...": "raw calculator output" },
      "created_at": "2026-09-28T10:15:47"
    }
  ]
}
```

`GET /api/stats`

Scenario usage aggregated in SQL (`GROUP BY scenario`), not in Python.

```json
{
  "total_sessions": 128,
  "total_computations": 94,
  "by_scenario": [
    { "scenario": "emi_comparison", "runs": 51, "last_run_at": "2026-09-28T10:15:47" },
    { "scenario": "opportunity_cost", "runs": 43, "last_run_at": "2026-09-28T09:02:11" }
  ]
}
```

`GET /api/health` — returns `{"status": "ok", "database": "ok"}`, and fails if the
database is unreachable, so a platform health check catches a broken DB connection rather
than reporting a healthy process in front of a dead dependency.

Interactive OpenAPI docs are served by FastAPI at `/docs`, with the raw schema at
`/openapi.json`.

## Deployment

- **Frontend (Vercel):** `frontend/vercel.json` handles SPA routing. Set
  `VITE_API_BASE_URL` to your deployed backend URL in Vercel's project env vars.
- **Backend (Render or Railway):** `backend/Dockerfile` builds the FastAPI app;
  `backend/render.yaml` is a ready-to-use Render blueprint. Set `OPENAI_API_KEY`,
  `CORS_ORIGINS` (your Vercel domain), and `DATABASE_URL` as env vars on whichever platform
  you use.
- **Database:** any managed MySQL works (Aiven, Railway, Amazon RDS). Note that Render
  itself offers only Postgres and Key Value, so on Render the database has to come from
  elsewhere. Point `DATABASE_URL` at it in the form
  `mysql+pymysql://user:password@host:3306/recoverai?charset=utf8mb4`. A bare `mysql://`
  URL from the provider is accepted too and is rewritten to use PyMySQL.
- **Database TLS:** managed providers usually require TLS. Append `ssl_ca` to the
  connection string and SQLAlchemy passes it through to PyMySQL, so no code change is
  needed:
  `...?charset=utf8mb4&ssl_ca=/etc/secrets/ca.pem`. On Render, upload the provider's CA
  certificate as a Secret File, which lands in `/etc/secrets/`.

## Example walkthroughs

### 4a. SIP-Pause-vs-Loan-Payoff

**Input:** "What if I pause my ₹5,000/month SIP (expecting 10% annual return) for 6
months to put extra money toward my ₹5,00,000 personal loan at 10% interest, which has
36 months left?"

**Extracted params:**
```json
{
  "scenario": "sip_pause_vs_loan_payoff",
  "monthly_sip_amount": 5000,
  "expected_annual_return_pct": 10,
  "loan_outstanding_amount": 500000,
  "loan_interest_rate_pct": 10,
  "loan_remaining_tenure_months": 36,
  "pause_duration_months": 6
}
```

**Calculator output (abridged):**
```json
{
  "scenario_a": { "label": "Continue SIP", "loan_total_interest": 80809.37, "loan_months_taken": 36, "sip_final_corpus": 210650.01 },
  "scenario_b": { "label": "Pause & Pay Off Loan", "loan_total_interest": 71765.70, "loan_months_taken": 34, "sip_final_corpus": 171031.06 },
  "comparison": { "loan_interest_saved": 9043.67, "loan_tenure_reduced_months": 2, "sip_corpus_difference": -39618.95, "net_financial_difference": -30575.28 }
}
```

Here pausing the SIP saves ~₹9,000 in loan interest and shaves 2 months off the tenure,
but costs ~₹39,600 in foregone SIP growth — a net negative in this case, which is exactly
the kind of trade-off the explainer node surfaces instead of quietly picking a winner.

### 4b. EMI Comparison

**Input:** "Compare two loan offers: ₹5,00,000 at 9% for 60 months vs ₹5,00,000 at 11%
for 60 months."

**Calculator output:**
```json
{
  "offers": [
    { "label": "Bank A", "principal": 500000, "annual_interest_rate_pct": 9, "tenure_months": 60, "emi": 10379.87, "total_interest_paid": 122792.20, "total_amount_repaid": 622792.20 },
    { "label": "Bank B", "principal": 500000, "annual_interest_rate_pct": 11, "tenure_months": 60, "emi": 10871.28, "total_interest_paid": 152276.80, "total_amount_repaid": 652276.80 }
  ],
  "lowest_total_interest_offer": "Bank A"
}
```

### 4c. Opportunity Cost Calculator

**Input:** "Should I invest a ₹2,00,000 lump sum at an expected 12% return, or use it to
prepay a loan at 9% interest, over the next 24 months?"

**Calculator output:**
```json
{
  "prepayment_option": { "label": "Prepay Loan", "guaranteed_interest_saved": 39282.71, "risk": "none (guaranteed)" },
  "investment_option": { "label": "Invest Instead", "projected_future_value": 253946.93, "projected_growth": 53946.93, "risk": "market risk (not guaranteed)" },
  "comparison": { "projected_advantage_of_investing": 14664.22 }
}
```

Both sides use the *same* compounding methodology, which matters: paying down a
reducing-balance loan is financially equivalent to a risk-free investment compounding at
the loan's own rate (every rupee of principal avoided also avoids the interest that would
have accrued on it every subsequent period), so `guaranteed_interest_saved` is computed as
`lump_sum * [(1 + monthly_rate)^n - 1]` — not a flat simple-interest estimate. Comparing a
simple-interest loan number against a compound-interest investment number would silently
understate the loan side and make investing look better than it is; see
`test_opportunity_cost_prepayment_uses_compound_not_simple_interest` in
`backend/tests/test_calculators.py` for the regression guard.

The explainer node is prompted to always state explicitly that the investment number is
projected and not guaranteed, while the prepayment savings are guaranteed — this is
enforced in `EXPLAINER_SYSTEM_PROMPT` in `backend/app/graph.py`, not left to chance.

## Non-goals

No auth (sessions are identified by an unguessable client-generated id, not owned by a
user account), no scenarios beyond the 3 above, no tax-law-specific calculations (called
out as an assumption instead), no real bank/investment API integrations.
