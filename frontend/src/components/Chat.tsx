import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";

interface Props {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  loading: boolean;
  prefillText?: string;
  prefillKey?: number;
}

export default function Chat({ messages, onSend, loading, prefillText, prefillKey }: Props) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (prefillText === undefined) return;
    setInput(prefillText);
    textareaRef.current?.focus();
  }, [prefillKey]);

  const submit = () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setInput("");
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
      {messages.length > 0 && (
        <div className="flex flex-col gap-3">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                m.role === "user"
                  ? "self-end bg-[var(--ink)] text-[var(--paper)]"
                  : "self-start bg-[var(--paper-soft)] text-[var(--ink)]"
              }`}
            >
              {m.content}
            </div>
          ))}
          {loading && (
            <div className="self-start rounded-2xl bg-[var(--paper-soft)] px-4 py-2.5 text-sm text-[var(--ink-muted)]">
              Thinking…
            </div>
          )}
        </div>
      )}

      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder='e.g. "What if I pause my SIP for 6 months to pay off a personal loan faster?"'
          rows={2}
          className="flex-1 resize-none rounded-xl border border-[var(--ink)]/15 bg-white/70 px-4 py-3 text-sm text-[var(--ink)] placeholder:text-[var(--ink-muted)] focus:border-[var(--accent-strong)] focus:outline-none"
        />
        <button
          onClick={submit}
          disabled={loading || !input.trim()}
          className="btn-primary rounded-xl px-5 py-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </div>
  );
}
