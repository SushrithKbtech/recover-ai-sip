export default function SiteNav() {
  const scrollTo = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <header className="nav-blur sticky top-0 z-40 border-b border-line">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 sm:px-10">
        <a href="#top" onClick={scrollTo("top")} className="font-display text-lg tracking-tight text-foreground">
          Recover<span className="text-accent">AI</span>
        </a>
        <nav className="hidden items-center gap-8 text-sm text-muted sm:flex">
          <a href="#how-it-works" onClick={scrollTo("how-it-works")} className="link-wipe hover:text-foreground">
            How it works
          </a>
          <a href="#features" onClick={scrollTo("features")} className="link-wipe hover:text-foreground">
            Capabilities
          </a>
          <a href="#scenarios" onClick={scrollTo("scenarios")} className="link-wipe hover:text-foreground">
            Scenarios
          </a>
        </nav>
        <a
          href="#console"
          onClick={scrollTo("console")}
          className="btn-primary rounded-sm px-4 py-2 text-xs font-semibold tracking-wide"
        >
          Try it
        </a>
      </div>
    </header>
  );
}
