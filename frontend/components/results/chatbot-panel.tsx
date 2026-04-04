"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import type { AnalysisReport } from "@/lib/types";

interface ChatbotPanelProps {
  jobId: string;
  report: AnalysisReport;
  isOpen: boolean;
  onClose: () => void;
  provider?: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

function generateStarterPrompts(report: AnalysisReport): string[] {
  const prompts: string[] = [];

  const topRegion = report.scores.region_breakdown
    .sort((a, b) => b.normalized_score - a.normalized_score)[0];
  if (topRegion) {
    prompts.push(`Why is ${topRegion.region_name} so active?`);
  }

  if (report.dark_patterns.patterns.length > 0) {
    prompts.push("What dark patterns were detected?");
  }

  const peaks = report.timeline.peaks;
  if (peaks.length > 0) {
    prompts.push(
      `Explain the activation spike at ${peaks[0].time_s.toFixed(1)}s`,
    );
  }

  if (report.scores.emotion_score > 5) {
    prompts.push("Why is the emotion score elevated?");
  }

  prompts.push("Give me a plain-language summary of this analysis");

  return prompts.slice(0, 4);
}

export function ChatbotPanel({
  jobId,
  report,
  isOpen,
  onClose,
  provider = "AI",
}: ChatbotPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const starterPrompts = generateStarterPrompts(report);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: text.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);

      try {
        const res = await fetch(`/api/chat/${encodeURIComponent(jobId)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text.trim(),
            history: messages.map((m) => ({
              role: m.role,
              content: m.content,
            })),
          }),
        });

        if (!res.ok) {
          throw new Error(`Chat failed: ${res.status}`);
        }

        const contentType = res.headers.get("content-type") || "";

        if (contentType.includes("text/event-stream") && res.body) {
          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let accumulated = "";
          const assistantId = crypto.randomUUID();

          setMessages((prev) => [
            ...prev,
            {
              id: assistantId,
              role: "assistant",
              content: "",
              timestamp: new Date(),
            },
          ]);

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split("\n");
            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const data = line.slice(6);
                if (data === "[DONE]") continue;
                try {
                  const parsed = JSON.parse(data);
                  accumulated += parsed.content || parsed.text || "";
                } catch {
                  accumulated += data;
                }
              }
            }
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: accumulated } : m,
              ),
            );
          }
        } else {
          const data = await res.json();
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content:
                data.content || data.message || data.text || "No response",
              timestamp: new Date(),
            },
          ]);
        }
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content:
              err instanceof Error
                ? `Error: ${err.message}`
                : "Something went wrong. The AI assistant may be unavailable.",
            timestamp: new Date(),
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [jobId, messages, isLoading],
  );

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="animate-slide-in-right fixed bottom-0 right-0 top-0 z-50 flex w-full max-w-md flex-col border-l border-slate-800/80 bg-[#0a0e1a]/98 shadow-2xl backdrop-blur-md">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800/60 px-5 py-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-200">
              AI Assistant
            </h3>
            <p className="text-[10px] text-slate-500">
              Powered by {provider} · AI-generated responses
            </p>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-800 hover:text-slate-300"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="scrollbar-thin flex-1 space-y-4 overflow-y-auto px-5 py-4"
        >
          {messages.length === 0 && (
            <div className="space-y-3 pt-4">
              <p className="text-center text-xs text-slate-500">
                Ask questions about your brain analysis results
              </p>
              <div className="space-y-2">
                {starterPrompts.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(prompt)}
                    className="w-full rounded-xl border border-slate-800/60 bg-slate-900/30 px-4 py-2.5 text-left text-xs text-slate-400 transition hover:border-cyan-500/20 hover:text-slate-300"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
                  msg.role === "user"
                    ? "bg-cyan-500/15 text-slate-200"
                    : "border border-slate-800/40 bg-slate-900/40 text-slate-300"
                }`}
              >
                {msg.role === "assistant" && (
                  <span className="mb-1 block text-[9px] font-medium uppercase tracking-widest text-violet-400/60">
                    AI-generated
                  </span>
                )}
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.role === "assistant" && !msg.content && isLoading && (
                  <span className="inline-flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-500" />
                    <span
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-500"
                      style={{ animationDelay: "150ms" }}
                    />
                    <span
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-500"
                      style={{ animationDelay: "300ms" }}
                    />
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input */}
        <form
          onSubmit={handleSubmit}
          className="border-t border-slate-800/60 px-4 py-3"
        >
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your results..."
              disabled={isLoading}
              className="min-w-0 flex-1 rounded-xl border border-slate-800/60 bg-slate-900/50 px-4 py-2.5 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-500/30 focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 text-white transition hover:brightness-110 disabled:opacity-30"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z" />
              </svg>
            </button>
          </div>
          <p className="mt-2 text-center text-[9px] text-slate-700">
            AI responses are generated, not verified analysis data
          </p>
        </form>
      </div>
    </>
  );
}
