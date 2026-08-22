const steps = [
  {
    t: "You describe it",
    d: "“What if I pause my SIP for 6 months to pay off my loan faster?” — no forms, no dropdowns.",
  },
  {
    t: "It asks what's missing",
    d: "Only the numbers it actually needs — your loan rate, say — and only if you didn't already give them.",
  },
  {
    t: "The math runs, not the model",
    d: "A tested calculator computes both scenarios. The AI is not allowed to touch a single number.",
  },
  {
    t: "You get both sides",
    d: "A plain-language comparison, two outcome cards, a chart, and every assumption spelled out.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-b border-line py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-6 sm:px-10">
        <p className="text-[10px] uppercase tracking-[0.2em] text-accent">From question to answer</p>
        <h2 className="mt-3 max-w-xl font-display text-3xl leading-tight sm:text-[2.4rem]">
          Four steps. No spreadsheet required.
        </h2>

        <div className="mt-14 flex flex-col gap-8 sm:gap-10">
          {steps.map((s, i) => (
            <div key={s.t} className="flex items-start gap-5 sm:gap-6">
              <div className="flex flex-col items-center">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] font-display text-base text-accent">
                  {i + 1}
                </div>
                {i < steps.length - 1 && (
                  <div className="mt-2 h-full w-px flex-1 bg-[var(--line-strong)] sm:hidden" />
                )}
              </div>
              <div className="pb-2">
                <h3 className="font-display text-lg text-foreground sm:text-xl">{s.t}</h3>
                <p className="mt-1.5 max-w-md text-sm leading-relaxed text-muted sm:text-[15px]">
                  {s.d}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
