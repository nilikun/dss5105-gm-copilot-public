import clsx from "clsx";
import {
  Bell, BellRing, ClipboardList, Clock3, FastForward, Menu, MessageSquare, Newspaper, Plus, ScrollText, Settings,
  SquareCheckBig,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AppState, Conversation } from "../types";
import { Sparkle } from "./Sparkle";
import { IconButton } from "./ui";

export type View = "chat" | "briefing" | "alerts" | "actions" | "watches" | "logs" | "settings";

export function Sidebar({ open, setOpen, view, setView, state, conversations, activeConv, onNewChat, onOpenConv }: {
  open: boolean; setOpen: (b: boolean) => void; view: View; setView: (v: View) => void; state: AppState | null;
  conversations: Conversation[]; activeConv: string | null; onNewChat: () => void; onOpenConv: (id: string) => void;
}) {
  const nav: { id: View; label: string; icon: typeof Bell; badge?: number }[] = [
    { id: "briefing", label: "Morning briefing", icon: Newspaper },
    { id: "alerts", label: "Alerts", icon: Bell, badge: state?.unread_alerts },
    { id: "actions", label: "Actions", icon: SquareCheckBig, badge: state?.pending_actions },
    { id: "watches", label: "Watches", icon: BellRing, badge: state?.active_watches },
    { id: "logs", label: "Thinking logs", icon: ScrollText },
  ];
  const go = (v: View) => { setView(v); if (window.innerWidth < 1024) setOpen(false); };
  return (
    <>
      {open && <div className="fixed inset-0 z-20 bg-black/20 lg:hidden" onClick={() => setOpen(false)} />}
      <aside className={clsx("fixed z-30 flex h-full flex-col bg-surface-2 transition-all duration-200 lg:static",
        open ? "w-72 translate-x-0" : "w-72 -translate-x-full lg:w-[68px] lg:translate-x-0")}>
        <div className="flex h-16 items-center px-3">
          <IconButton label="Menu" onClick={() => setOpen(!open)}><Menu size={22} /></IconButton>
        </div>
        <div className="px-3">
          <button onClick={() => { onNewChat(); go("chat"); }}
            className={clsx("flex h-11 items-center gap-3 rounded-full bg-surface-3 text-sm text-ink-2 hover:bg-[#dde3ea]",
              open ? "px-4" : "w-11 justify-center")}>
            <Plus size={20} />{open && "New chat"}
          </button>
        </div>
        <nav className="mt-4 space-y-0.5 px-3">
          {nav.map(({ id, label, icon: Icon, badge }) => (
            <button key={id} onClick={() => go(id)} title={label}
              className={clsx("relative flex h-10 w-full items-center gap-3 rounded-full text-sm",
                open ? "px-4" : "justify-center", view === id ? "bg-accent-soft font-medium text-[#041e49]" : "text-ink-2 hover:bg-surface-3")}>
              <Icon size={18} />{open && <span className="flex-1 text-left">{label}</span>}
              {!!badge && (open
                ? <span className="rounded-full bg-accent px-2 text-xs text-white">{badge}</span>
                : <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-bad" />)}
            </button>
          ))}
        </nav>
        {open && (
          <div className="mt-6 min-h-0 flex-1 overflow-y-auto px-3">
            <p className="px-4 pb-1 text-xs font-medium text-ink-3">Recent</p>
            {conversations.map((c) => (
              <button key={c.conversation_id} onClick={() => { onOpenConv(c.conversation_id); go("chat"); }}
                className={clsx("flex h-9 w-full items-center gap-3 rounded-full px-4 text-left text-sm",
                  activeConv === c.conversation_id && view === "chat" ? "bg-accent-soft text-[#041e49]" : "text-ink-2 hover:bg-surface-3")}>
                <MessageSquare size={15} className="shrink-0" /><span className="truncate">{c.title}</span>
              </button>
            ))}
          </div>
        )}
        <div className={clsx("mt-auto px-3 pb-4", !open && "flex justify-center")}>
          <button onClick={() => go("settings")} title="Settings"
            className={clsx("flex h-10 items-center gap-3 rounded-full text-sm",
              open ? "w-full px-4" : "w-10 justify-center", view === "settings" ? "bg-accent-soft text-[#041e49]" : "text-ink-2 hover:bg-surface-3")}>
            <Settings size={18} />{open && "Settings"}
          </button>
        </div>
      </aside>
    </>
  );
}

export function TopBar({ state, onMenu, onChanged, onAlerts }: { state: AppState | null; onMenu: () => void;
  onChanged: () => void; onAlerts: () => void }) {
  const [menu, setMenu] = useState(false);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setMenu(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  const advance = async (days: number, hours = 0) => {
    setBusy(true);
    try { await api.advance(days, hours); onChanged(); } finally { setBusy(false); setMenu(false); }
  };
  const toggleMode = async () => { if (state) { await api.setMode(state.mode === "sim" ? "real" : "sim"); onChanged(); } };
  const now = state ? new Date(state.now) : null;
  return (
    <header className="flex h-16 shrink-0 items-center gap-2 px-3">
      <IconButton label="Menu" onClick={onMenu} className="lg:hidden"><Menu size={22} /></IconButton>
      <div className="flex items-center gap-2 whitespace-nowrap text-lg text-ink sm:text-xl">
        <Sparkle size={22} /><span>GM Co-Pilot</span>
        {state && <span className="hidden rounded-lg bg-surface-2 px-2 py-0.5 text-xs text-ink-2 sm:inline">{state.settings.model}</span>}
      </div>
      <div className="ml-auto flex shrink-0 items-center gap-1">
        <div className="relative" ref={ref}>
          <button onClick={() => setMenu(!menu)} disabled={busy}
            className="flex h-9 items-center gap-2 whitespace-nowrap rounded-full bg-surface-2 px-3 text-sm text-ink-2 hover:bg-surface-3">
            <Clock3 size={16} className={clsx(busy && "gem-spin")} />
            <span className="hidden sm:inline">{now ? now.toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"}</span>
            <span className="sm:hidden">{now ? now.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"}</span>
            <span className="hidden text-xs text-ink-3 sm:inline">· {state?.mode === "real" ? "real time" : "simulated"}</span>
          </button>
          {menu && state && (
            <div className="absolute right-0 top-11 z-30 w-64 rounded-2xl bg-white p-2 shadow-[0_4px_16px_rgba(60,64,67,.25)]">
              <p className="px-3 py-2 text-xs text-ink-3">Scenario <b>{state.scenario}</b> · data through {state.data_through}</p>
              {state.mode === "sim" ? (
                [[0, 1, "Advance 1 hour"], [1, 0, "Advance 1 day (07:00)"], [2, 0, "Advance 2 days"]].map(([d, h, l]) => (
                  <button key={String(l)} onClick={() => advance(Number(d), Number(h))}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-ink hover:bg-surface-2">
                    <FastForward size={16} /> {l}
                  </button>
                ))
              ) : <p className="px-3 py-2 text-sm text-ink-2">Real time: the clock follows the wall clock.</p>}
              <button onClick={toggleMode} className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-ink hover:bg-surface-2">
                <ClipboardList size={16} /> Switch to {state.mode === "sim" ? "real time" : "simulated time"}
              </button>
            </div>
          )}
        </div>
        <IconButton label="Alerts" onClick={onAlerts} className="relative">
          <Bell size={20} />
          {!!state?.unread_p1 && <span className="absolute right-2 top-2 size-2.5 rounded-full bg-bad" />}
        </IconButton>
        {state && (
          <span title="LLM spend today (UTC) / daily cap" className="hidden rounded-full px-2 text-xs text-ink-3 md:inline">
            ${state.usage.cost_usd.toFixed(4)} / ${state.usage.daily_budget_usd.toFixed(0)}
          </span>
        )}
      </div>
    </header>
  );
}
