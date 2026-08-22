import PipelineTrace from "./PipelineTrace";

interface Props {
  onTry: () => void;
}

export default function Hero({ onTry }: Props) {
  const scrollTo = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section id="top" className="relative overflow-hidden border-b border-line">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.1]"
        style={{
          backgroundImage:
            "linear-gradient(var(--line-strong) 1px, transparent 1px), linear-gradient(90deg, var(--line-strong) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
          maskImage: "radial-gradient(ellipse at 50% 10%, black 0%, transparent 70%)",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 50% 32%, rgba(224,138,60,0.16), transparent 55%), radial-gradient(ellipse at 50% 100%, rgba(20,15,11,0.9), transparent 60%)",
        }}
      />

      <div className="relative mx-auto grid max-w-6xl items-center gap-16 px-6 py-24 sm:px-10 sm:py-32 lg:grid-cols-[1.1fr_0.9fr] lg:text-left">
        <div className="text-center lg:text-left">
          <div className="animate-fade-up" style={{ animationDelay: "60ms" }}>
            <span className="inline-flex items-center gap-2.5 rounded-full border border-line-strong bg-black/25 px-4 py-1.5 text-[10px] uppercase tracking-[0.2em] text-muted backdrop-blur-sm">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-70" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
              </span>
              Agentic financial reasoning, grounded in real math
            </span>
          </div>

          <h1
            className="animate-fade-up mt-8 font-display text-[2.6rem] leading-[1.08] tracking-tight sm:text-[4rem]"
            style={{ animationDelay: "160ms" }}
          >
            Know the number
            <br />
            <span className="warm-text italic">before you decide.</span>
          </h1>

          <p
            className="animate-fade-up mx-auto mt-7 max-w-xl text-[15px] leading-relaxed text-muted sm:text-lg lg:mx-0"
            style={{ animationDelay: "280ms" }}
          >
            Describe a money decision in plain language. An LLM agent routes it to the right
            calculator and asks only for what's missing — then a deterministic engine runs the
            actual math, so every number you see was computed, never guessed.
          </p>

          <div
            className="animate-fade-up mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row lg:justify-start"
            style={{ animationDelay: "380ms" }}
          >
            <button onClick={onTry} className="btn-primary rounded-sm px-8 py-3.5 text-sm font-semibold tracking-wide">
              Try a scenario
            </button>
            <a
              href="#how-it-works"
              onClick={scrollTo("how-it-works")}
              className="btn-ghost rounded-sm px-8 py-3.5 text-sm font-medium text-foreground"
            >
              How it works
            </a>
          </div>

          <div className="animate-fade-up mt-16 flex justify-center gap-12 lg:justify-start" style={{ animationDelay: "480ms" }}>
            {[
              ["3", "grounded calculators"],
              ["0", "numbers invented by the model"],
              ["100%", "assumptions disclosed"],
            ].map(([s, l]) => (
              <div key={l}>
                <p className="font-display text-2xl text-accent sm:text-3xl">{s}</p>
                <p className="mt-1 text-[10px] uppercase tracking-[0.15em] text-muted">{l}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="animate-fade-up flex justify-center lg:justify-end" style={{ animationDelay: "460ms" }}>
          <PipelineTrace />
        </div>
      </div>
    </section>
  );
}
