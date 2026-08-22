const features = [
  {
    k: "1",
    title: "Agentic scenario routing",
    body: "One structured reasoning pass decides which of the three calculators your question actually maps to — real branching logic, not a hardcoded intent list.",
  },
  {
    k: "2",
    title: "Adaptive clarification",
    body: "Missing a rate or a tenure? The agent asks for exactly that field, then folds your answer back into the same conversation instead of starting over.",
  },
  {
    k: "3",
    title: "Tool-grounded math",
    body: "Every figure comes from a pure, unit-tested Python function. The model calls the tool and reads its output — it never performs arithmetic itself.",
  },
  {
    k: "4",
    title: "Retrieval-style grounding",
    body: "The write-up is constrained to only cite numbers that exist in the calculator's own output — the same discipline that keeps RAG systems honest, applied to numbers instead of documents.",
  },
  {
    k: "5",
    title: "Stateful multi-turn memory",
    body: "Clarifying answers merge into the same extraction context on the next turn, so the agent never restarts the conversation from zero.",
  },
  {
    k: "6",
    title: "Disclosed assumptions",
    body: "Fixed rates, no tax modeling, no prepayment penalties — every simplification is surfaced in its own section, not buried in a footnote.",
  },
];

export default function Features() {
  return (
    <section id="features" className="border-b border-line py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-6 sm:px-10">
        <p className="text-[10px] uppercase tracking-[0.2em] text-accent">Under the hood</p>
        <h2 className="mt-3 max-w-2xl font-display text-3xl leading-tight sm:text-[2.4rem]">
          Built for grounded, agentic reasoning —{" "}
          <span className="warm-text">not vibes.</span>
        </h2>

        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.k} className="tile h-full p-6">
              <span className="tile-badge font-display">{f.k}</span>
              <h3 className="mt-4 font-display text-lg text-foreground">{f.title}</h3>
              <p className="mt-2.5 text-sm leading-relaxed text-muted">{f.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
