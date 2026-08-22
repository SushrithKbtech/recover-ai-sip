interface Scenario {
  tag: string;
  title: string;
  question: string;
  prompt: string;
}

const scenarios: Scenario[] = [
  {
    tag: "SIP vs. loan payoff",
    title: "Pause your SIP, or keep investing?",
    question: "Should you redirect a running SIP to kill a loan faster, or let both run in parallel?",
    prompt:
      "What if I pause my ₹5,000/month SIP (10% expected return) for 6 months to pay off my ₹5,00,000 personal loan at 10% interest, which has 36 months left?",
  },
  {
    tag: "EMI comparison",
    title: "Which loan offer actually costs less?",
    question: "Two offers, two rates, two tenures — which one costs less once the interest is totaled up?",
    prompt: "Compare a ₹5,00,000 loan at 9% for 60 months against one at 11% for 60 months.",
  },
  {
    tag: "Opportunity cost",
    title: "Invest the lump sum, or prepay the loan?",
    question: "Guaranteed interest saved vs. projected (uncertain) investment growth over the same horizon.",
    prompt:
      "Should I invest a ₹2,00,000 lump sum at an expected 12% return, or use it to prepay a loan at 9% interest, over the next 24 months?",
  },
];

interface Props {
  onTry: (prompt: string) => void;
}

export default function ScenarioShowcase({ onTry }: Props) {
  return (
    <section id="scenarios" className="border-b border-line py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-6 sm:px-10">
        <p className="text-[10px] uppercase tracking-[0.2em] text-accent">Three calculators</p>
        <h2 className="mt-3 max-w-2xl font-display text-3xl leading-tight sm:text-[2.4rem]">
          Purpose-built, not general advice.
        </h2>
        <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-muted">
          RecoverAI only answers what these three engines can actually compute. Ask something
          outside that scope and it says so, instead of guessing.
        </p>

        <div className="mt-14 grid gap-5 lg:grid-cols-3">
          {scenarios.map((s) => (
            <div key={s.tag} className="tile flex h-full flex-col p-6">
              <p className="text-[10px] uppercase tracking-[0.15em] text-accent/85">{s.tag}</p>
              <h3 className="mt-4 font-display text-xl text-foreground">{s.title}</h3>
              <p className="mt-2.5 flex-1 text-sm leading-relaxed text-muted">{s.question}</p>
              <button
                onClick={() => onTry(s.prompt)}
                className="link-wipe mt-6 self-start text-sm text-accent"
              >
                Try this scenario →
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
