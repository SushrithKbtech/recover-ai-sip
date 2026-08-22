import { useEffect, useState } from "react";

interface Stage {
  title: string;
  rows: [string, string][];
  result: string;
}

const PROMPT = '"Pause my SIP for 6 months to pay off my loan faster?"';

const STAGES: Stage[] = [
  {
    title: "Understanding",
    rows: [
      ["monthly_sip_amount", "₹5,000"],
      ["expected_annual_return_pct", "10%"],
      ["loan_outstanding_amount", "₹5,00,000"],
      ["loan_interest_rate_pct", "10%"],
      ["loan_remaining_tenure_months", "36"],
      ["pause_duration_months", "6"],
    ],
    result: "→ routed to sip_pause_vs_loan_payoff",
  },
  {
    title: "Calculating",
    rows: [
      ["scenario_a.total_interest", "₹80,809"],
      ["scenario_b.total_interest", "₹71,766"],
      ["loan_tenure_reduced", "2 months"],
      ["net_financial_difference", "−₹30,575"],
    ],
    result: "→ 0 model calls this step",
  },
  {
    title: "Explaining",
    rows: [
      ["cites only", "calculator output"],
      ["assumptions disclosed", "3"],
    ],
    result: "→ “saves ₹9,044 in interest, costs ₹39,619 in SIP growth”",
  },
];

export default function PipelineTrace() {
  const [stageIdx, setStageIdx] = useState(0);
  const [rowIdx, setRowIdx] = useState(0);

  useEffect(() => {
    const stage = STAGES[stageIdx];
    const finishedRows = rowIdx >= stage.rows.length;
    const delay = !finishedRows ? 420 : stageIdx < STAGES.length - 1 ? 900 : 2200;

    const timer = setTimeout(() => {
      if (!finishedRows) {
        setRowIdx(rowIdx + 1);
      } else if (stageIdx < STAGES.length - 1) {
        setStageIdx(stageIdx + 1);
        setRowIdx(0);
      } else {
        setStageIdx(0);
        setRowIdx(0);
      }
    }, delay);

    return () => clearTimeout(timer);
  }, [stageIdx, rowIdx]);

  return (
    <div className="glass-panel w-full max-w-sm rounded-2xl p-5 font-mono text-[13px] sm:p-6">
      <div className="flex items-center gap-2 border-b border-line pb-3">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-70" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
        </span>
        <span className="text-[10px] uppercase tracking-[0.2em] text-muted">agent trace</span>
      </div>

      <p className="mt-4 truncate text-[12px] text-muted">{PROMPT}</p>

      <div className="mt-5 flex flex-col">
        {STAGES.map((stage, i) => {
          const status = i < stageIdx ? "done" : i === stageIdx ? "active" : "pending";
          const visibleCount = i < stageIdx ? stage.rows.length : i === stageIdx ? Math.min(rowIdx, stage.rows.length) : 0;
          const showResult = visibleCount === stage.rows.length && (status === "done" || (status === "active" && rowIdx >= stage.rows.length));

          return (
            <div key={stage.title} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] transition-colors duration-300 ${
                    status === "done"
                      ? "bg-accent text-[var(--ink)]"
                      : status === "active"
                        ? "border border-accent text-accent"
                        : "border border-line-strong text-muted"
                  }`}
                >
                  {status === "done" ? "✓" : i + 1}
                </div>
                {i < STAGES.length - 1 && (
                  <div
                    className={`w-px flex-1 ${status === "done" ? "bg-accent/50" : "bg-[var(--line-strong)]"}`}
                    style={{ minHeight: "1.25rem" }}
                  />
                )}
              </div>

              <div className={`min-w-0 flex-1 pb-5 transition-opacity duration-300 ${status === "pending" ? "opacity-35" : "opacity-100"}`}>
                <p className={`text-[11px] uppercase tracking-[0.14em] ${status === "active" ? "text-accent" : "text-foreground"}`}>
                  {stage.title}
                </p>
                <div className="mt-2 space-y-1">
                  {stage.rows.slice(0, visibleCount).map(([k, v]) => (
                    <div key={k} className="flex items-baseline justify-between gap-3 text-[11.5px]">
                      <span className="truncate text-muted">{k}</span>
                      <span className="shrink-0 text-foreground">{v}</span>
                    </div>
                  ))}
                </div>
                {showResult && (
                  <p className="mt-2 text-[11.5px] leading-snug text-accent">{stage.result}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
