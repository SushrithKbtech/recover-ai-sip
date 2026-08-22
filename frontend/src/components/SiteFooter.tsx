export default function SiteFooter() {
  return (
    <footer className="border-t border-line py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 text-center sm:flex-row sm:text-left sm:px-10">
        <p className="font-display text-sm text-foreground">
          Recover<span className="text-accent">AI</span>
        </p>
        <p className="text-xs text-muted">
          Not financial advice. Three calculators, deterministic math, disclosed assumptions.
        </p>
      </div>
    </footer>
  );
}
