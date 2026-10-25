import { ArrowRight, CalendarClock, Factory, Lightbulb, MessageSquareWarning } from "lucide-react";
import { useEffect, useRef } from "react";
import type { AppState, Briefing } from "../types";
import { Composer } from "./Composer";
import { AssistantMessage, type ChatItem, UserBubble } from "./Message";

const SUGGESTIONS = [
  { icon: Lightbulb, text: "Anything I should know this morning?" },
  { icon: Factory, text: "A customer wants 800 hoodies by the 25th. Can we take it?" },
  { icon: MessageSquareWarning, text: "How is the TrendCart order doing?" },
  { icon: CalendarClock, text: "Tell me if ORD-120 hasn't moved by Friday." },
];

export function ChatView({ items, running, onSend, onEvidence, onChanged, state, briefing, openBriefing }: {
  items: ChatItem[]; running: boolean; onSend: (t: string) => void; onEvidence: (id: string) => void;
  onChanged: () => void; state: AppState | null; briefing: Briefing | null; openBriefing: () => void;
}) {
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [items]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <Welcome state={state} briefing={briefing} onSend={onSend} openBriefing={openBriefing} />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
            {items.map((it) => it.role === "user"
              ? <UserBubble key={it.id} text={it.text} />
              : <AssistantMessage key={it.id} item={it} onSend={onSend} onEvidence={onEvidence} onChanged={onChanged} />)}
            <div ref={bottom} />
          </div>
        )}
      </div>
      <Composer onSend={onSend} disabled={running} />
    </div>
  );
}

function Welcome({ state, briefing, onSend, openBriefing }: { state: AppState | null; briefing: Briefing | null;
  onSend: (t: string) => void; openBriefing: () => void }) {
  const when = state ? new Date(state.now).toLocaleString("en-GB", { weekday: "long", day: "numeric", month: "long",
    hour: "2-digit", minute: "2-digit" }) : "";
  const s = briefing?.structured;
  const top = s ? [...s.yesterday, ...s.at_risk].slice(0, 3) : [];
  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col justify-center px-4 py-10 sm:px-6">
      <h1 className="text-4xl font-medium leading-tight sm:text-5xl">
        <span className="gem-gradient-text">Hello, Manager</span>
      </h1>
      <p className="mt-2 text-2xl text-[#c4c7c5] sm:text-3xl">What do you need to know?</p>
      {when && <p className="mt-3 text-sm text-ink-3">Factory time: {when} · data through {state?.data_through}</p>}

      {briefing && (
        <button onClick={openBriefing}
          className="group mt-8 w-full rounded-3xl bg-surface-2 p-5 text-left transition-colors hover:bg-surface-3">
          <div className="mb-2 flex items-center justify-between text-sm font-medium text-ink-2">
            Morning briefing · {briefing.date}
            <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
          </div>
          {briefing.narrative ? (
            <p className="line-clamp-4 text-[15px] leading-relaxed text-ink">{briefing.narrative}</p>
          ) : (
            <ul className="space-y-1.5 text-[15px] text-ink">
              {top.map((i, n) => <li key={n} className="line-clamp-2">• {i.text}</li>)}
            </ul>
          )}
        </button>
      )}

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map(({ icon: Icon, text }) => (
          <button key={text} onClick={() => onSend(text)}
            className="flex min-h-24 flex-col justify-between rounded-2xl bg-surface-2 p-4 text-left text-[15px] text-ink transition-colors hover:bg-surface-3">
            {text}
            <Icon size={20} className="mt-3 self-end text-ink-2" />
          </button>
        ))}
      </div>
    </div>
  );
}
