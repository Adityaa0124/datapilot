/**
 * DataPilot Frontend Main Application Component
 * Manages conversational session state, SSE streaming, and responsive UI layout.
 */
import {
  Activity,
  BarChart3,
  Eraser,
  History,
  Leaf,
  MessageSquarePlus,
  Server,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Composer } from "./components/Composer";
import { EmptyState } from "./components/EmptyState";
import { MessageBubble } from "./components/MessageBubble";
import { streamQuery } from "./lib/agentApi";
import { cn, summarizeResult } from "./lib/format";
import type { AgentEvent, ChatMessage, StepState } from "./types/agent";

const examples = [
  "Show the top five products with the highest sales this month",
  "Calculate the total GMV and average order value (AOV) for Q1 2025",
  "Rank all geographic regions by total revenue from highest to lowest",
  "Summarize order count and total spending grouped by customer member level",
];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "Vite /api proxy";

function makeId() {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function upsertStep(steps: StepState[] = [], event: Extract<AgentEvent, { type: "progress" }>) {
  const next = steps.filter((item) => item.step !== event.step);
  next.push({
    step: event.step,
    status: event.status,
    updatedAt: Date.now(),
  });
  return next;
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [activeController, setActiveController] = useState<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const isStreaming = Boolean(activeController);
  const canSubmit = draft.trim().length > 0 && !isStreaming;

  const completedCount = useMemo(
    () => messages.filter((message) => message.role === "assistant" && message.status === "done").length,
    [messages],
  );

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const startQuery = async (rawQuery = draft) => {
    const query = rawQuery.trim();
    if (!query || isStreaming) return;

    const userMessage: ChatMessage = {
      id: makeId(),
      role: "user",
      content: query,
      createdAt: Date.now(),
    };

    const assistantId = makeId();
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "Connecting to DataPilot Analyst...",
      createdAt: Date.now(),
      status: "streaming",
      steps: [],
    };

    const controller = new AbortController();
    setActiveController(controller);
    setDraft("");
    setMessages((current) => [...current, userMessage, assistantMessage]);

    const onEvent = (event: AgentEvent) => {
      setMessages((current) =>
        current.map((message) => {
          if (message.id !== assistantId) return message;

          if (event.type === "progress") {
            return {
              ...message,
              content: event.status === "running" ? `Executing step: ${event.step}` : message.content,
              steps: upsertStep(message.steps, event),
            };
          }

          if (event.type === "result") {
            return {
              ...message,
              content: summarizeResult(event.data),
              result: event.data,
              status: "done",
            };
          }

          if (event.type === "error") {
            return {
              ...message,
              error: event.message,
              status: "error",
            };
          }

          return message;
        }),
      );
    };

    try {
      await streamQuery(query, {
        onEvent,
        signal: controller.signal,
      });
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId && message.status === "streaming"
            ? { ...message, status: "done" }
            : message,
        ),
      );
    } catch (error: unknown) {
      if ((error as { name?: string })?.name === "AbortError") {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? { ...message, content: "Query execution stopped by user.", status: "done" }
              : message,
          ),
        );
      } else {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? {
                  ...message,
                  error: error instanceof Error ? error.message : "Failed to connect to backend server.",
                  status: "error",
                }
              : message,
          ),
        );
      }
    } finally {
      setActiveController(null);
    }
  };

  const stopQuery = () => {
    activeController?.abort();
  };

  const clearConversation = () => {
    if (isStreaming) return;
    setMessages([]);
    setDraft("");
  };

  return (
    <div className="h-dvh overflow-hidden bg-parchment text-ink">
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(90deg,rgba(32,32,29,0.045)_1px,transparent_1px),linear-gradient(rgba(32,32,29,0.035)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <div className="pointer-events-none fixed inset-0 grain" />

      <div className="relative grid h-full min-h-0 overflow-hidden lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="hidden min-h-0 border-r border-ink/10 bg-[#efe6d8]/85 backdrop-blur lg:flex lg:flex-col">
          <div className="border-b border-ink/10 px-5 py-5">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center bg-ink text-parchment">
                <BarChart3 className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <div className="text-base font-semibold tracking-[0.02em]">DataPilot</div>
                <div className="text-xs text-ink/50">Autonomous Database Analyst</div>
              </div>
            </div>
          </div>

          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4">
            <button
              type="button"
              onClick={clearConversation}
              disabled={isStreaming}
              className="flex h-11 w-full items-center justify-center gap-2 bg-ink text-sm font-semibold text-parchment transition hover:bg-soot disabled:cursor-not-allowed disabled:bg-ink/35"
            >
              <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
              New Session
            </button>

            <section>
              <div className="mb-2 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
                <History className="h-3.5 w-3.5" aria-hidden="true" />
                Example Queries
              </div>
              <div className="space-y-2">
                {examples.map((example) => (
                  <button
                    key={example}
                    type="button"
                    disabled={isStreaming}
                    onClick={() => startQuery(example)}
                    className="w-full border border-ink/10 bg-white/42 px-3 py-3 text-left text-sm leading-5 text-ink/75 transition hover:border-moss/35 hover:bg-white/75 disabled:cursor-not-allowed disabled:opacity-55"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </section>
          </div>

          <div className="border-t border-ink/10 p-4">
            <div className="grid gap-2 text-xs text-ink/55">
              <div className="flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2">
                  <Server className="h-3.5 w-3.5" aria-hidden="true" />
                  API Endpoint
                </span>
                <span className="truncate font-mono">{API_BASE_URL}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2">
                  <Activity className="h-3.5 w-3.5" aria-hidden="true" />
                  Queries Completed
                </span>
                <span>{completedCount}</span>
              </div>
            </div>
          </div>
        </aside>

        <main className="flex min-h-0 min-w-0 flex-col overflow-hidden">
          <header className="flex h-16 shrink-0 items-center justify-between border-b border-ink/10 bg-parchment/88 px-4 backdrop-blur lg:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <div className="grid h-9 w-9 shrink-0 place-items-center bg-moss text-white lg:hidden">
                <BarChart3 className="h-4 w-4" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-ink">DataPilot Autonomous Analyst</div>
                <div className="truncate text-xs text-ink/45">FastAPI SSE • LangGraph Multi-Agent Architecture</div>
              </div>
            </div>
            <button
              type="button"
              onClick={clearConversation}
              disabled={messages.length === 0 || isStreaming}
              className={cn(
                "grid h-9 w-9 place-items-center rounded-full text-ink/55 transition hover:bg-ink/5 hover:text-ink disabled:cursor-not-allowed disabled:opacity-35",
              )}
              title="Clear Session"
              aria-label="Clear Session"
            >
              <Eraser className="h-4 w-4" aria-hidden="true" />
            </button>
          </header>

          <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            {messages.length === 0 ? (
              <EmptyState examples={examples} onUseExample={(example) => setDraft(example)} />
            ) : (
              <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 lg:px-8">
                {messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}
              </div>
            )}
          </div>

          <div className="border-t border-ink/10 bg-[#efe6d8]/45 px-4 py-2 text-center text-xs text-ink/45">
            <span className="inline-flex items-center gap-2">
              <Leaf className="h-3.5 w-3.5 text-moss" aria-hidden="true" />
              {isStreaming ? "Processing Query..." : "System Ready"}
            </span>
          </div>
          <Composer
            value={draft}
            disabled={!canSubmit}
            isStreaming={isStreaming}
            onChange={setDraft}
            onSubmit={() => startQuery()}
            onStop={stopQuery}
          />
        </main>
      </div>
    </div>
  );
}
