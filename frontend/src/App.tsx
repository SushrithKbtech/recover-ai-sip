import { useState } from "react";
import SiteNav from "./components/SiteNav";
import Hero from "./components/Hero";
import HowItWorks from "./components/HowItWorks";
import Features from "./components/Features";
import ScenarioShowcase from "./components/ScenarioShowcase";
import SiteFooter from "./components/SiteFooter";
import Chat from "./components/Chat";
import ResultView from "./components/ResultView";
import { sendChatMessage } from "./api";
import type { ChatMessage, ResultPayload } from "./types";

function getOrCreateSessionId(): string {
  const existing = sessionStorage.getItem("recoverai_session_id");
  if (existing) return existing;
  const id = crypto.randomUUID();
  sessionStorage.setItem("recoverai_session_id", id);
  return id;
}

function scrollToConsole() {
  document.getElementById("console")?.scrollIntoView({ behavior: "smooth" });
}

export default function App() {
  const [sessionId] = useState(getOrCreateSessionId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [result, setResult] = useState<ResultPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prefillText, setPrefillText] = useState<string | undefined>(undefined);
  const [prefillKey, setPrefillKey] = useState(0);

  const handleTryScenario = (prompt?: string) => {
    setPrefillText(prompt ?? "");
    setPrefillKey((k) => k + 1);
    scrollToConsole();
  };

  const handleSend = async (message: string) => {
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setLoading(true);
    setError(null);

    try {
      const res = await sendChatMessage(sessionId, message);
      if (res.type === "clarifying_question") {
        setMessages((prev) => [...prev, { role: "assistant", content: res.message }]);
        setResult(null);
      } else if (res.type === "result" && res.result) {
        setMessages((prev) => [...prev, { role: "assistant", content: res.message }]);
        setResult(res.result);
      } else {
        setMessages((prev) => [...prev, { role: "assistant", content: res.message }]);
      }
    } catch (e) {
      setError("Couldn't reach RecoverAI. Please check the backend is running and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <SiteNav />

      <main>
        <Hero onTry={() => handleTryScenario()} />
        <HowItWorks />
        <Features />
        <ScenarioShowcase onTry={handleTryScenario} />

        <section id="console" className="py-24 sm:py-28">
          <div className="mx-auto max-w-3xl px-6 sm:px-10">
            <div className="text-center">
              <h2 className="font-display text-3xl leading-tight sm:text-[2.4rem]">
                Describe your scenario.
              </h2>
              <p className="mx-auto mt-4 max-w-lg text-[15px] leading-relaxed text-muted">
                Type a real number-driven question, or pick a scenario above to prefill one.
              </p>
            </div>

            <div className="mt-12 rounded-2xl border border-line-strong bg-[var(--paper)] p-6 shadow-[0_30px_70px_-30px_rgba(0,0,0,0.55)] sm:p-10">
              <Chat
                messages={messages}
                onSend={handleSend}
                loading={loading}
                prefillText={prefillText}
                prefillKey={prefillKey}
              />

              {error && (
                <p className="mx-auto mt-4 max-w-2xl rounded-lg border border-[var(--risk)]/40 bg-[var(--risk)]/10 px-4 py-3 text-sm text-[var(--risk)]">
                  {error}
                </p>
              )}

              {result && (
                <div className="mt-8">
                  <ResultView result={result} />
                </div>
              )}
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
