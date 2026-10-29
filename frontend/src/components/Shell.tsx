import clsx from "clsx";
import {
  Bell, BellRing, CalendarClock, Clock3, FastForward, Menu, MessageSquare, Newspaper, Plus, Radio, ScrollText,
  Settings, SquareCheckBig, Trash2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AppState, ClockInfo, Conversation } from "../types";
import { Sparkle } from "./Sparkle";
import { IconButton } from "./ui";

export type View = "chat" | "briefing" | "alerts" | "actions" | "watches" | "logs" | "settings";

export function Sidebar({ open, setOpen, view, setView, state, conversations, activeConv, onNewChat, onOpenConv,
  onDeleteConv, onClearConvs }: {
  open: boolean; setOpen: (b: boolean) => void; view: View; setView: (v: View) => void; state: AppState | null;
  conversations: Conversation[]; activeConv: string | null; onNewChat: () => void; onOpenConv: (id: string) => void;
  onDeleteConv: (id: string) => void; onClearConvs: () => void;
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
            <div className="flex items-center px-4 pb-1">
              <p className="flex-1 text-xs font-medium text-ink-3">Recent</p>
              {conversations.length > 0 && (
                <button onClick={onClearConvs} className="text-xs text-ink-3 hover:text-bad" title="Delete all chats">
                  Clear all
                </button>
              )}
            </div>
            {conversations.map((c) => (
              <div key={c.conversation_id}
                className={clsx("group flex h-9 items-center rounded-full pr-1",
                  activeConv === c.conversation_id && view === "chat" ? "bg-accent-soft text-[#041e49]" : "text-ink-2 hover:bg-surface-3")}>
                <button onClick={() => { onOpenConv(c.conversation_id); go("chat"); }}
                  className="flex h-full min-w-0 flex-1 items-center gap-3 pl-4 text-left text-sm">
                  <MessageSquare size={15} className="shrink-0" /><span className="truncate">{c.title}</span>
                </button>
                <button onClick={() => onDeleteConv(c.conversation_id)} aria-label={`Delete chat: ${c.title}`}
                  title="Delete chat"
                  className="grid size-7 shrink-0 place-items-center rounded-full text-ink-3 opacity-100 hover:bg-[#dde3ea] hover:text-bad lg:opacity-0 lg:group-hover:opacity-100 lg:focus:opacity-100">
                  <Trash2 size={14} />
                </button>
              </div>
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

const pad = (n: number) => String(n).padStart(2, "0");
/** "2026-04-03T07:00" for a datetime-local input, from the server's naive ISO string. */
const toInput = (iso: string) => iso.slice(0, 16);
const fmt = (iso: string, opts: Intl.DateTimeFormatOptions) => new Date(iso).toLocaleString("en-GB", opts);

function until(fromIso: string, toIso: string): string {
  const mins = Math.max(0, Math.round((new Date(toIso).getTime() - new Date(fromIso).getTime()) / 60000));
  const h = Math.floor(mins / 60);
  return h ? `${h} h ${pad(mins % 60)} min` : `${mins} min`;
}

export function TopBar({ state, onMenu, onChanged, onAlerts }: { state: AppState | null; onMenu: () => void;
  onChanged: () => void; onAlerts: () => void }) {
  const [menu, setMenu] = useState(false);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<ClockInfo | null>(null);
  const [when, setWhen] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setMenu(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  useEffect(() => {
    if (!menu) return;
    setMsg(null);
    api.clock().then((c) => { setInfo(c); setWhen(toInput(c.now)); }).catch(() => setInfo(null));
  }, [menu, state?.now, state?.mode]);

  const run = async (fn: () => Promise<unknown>, close = true) => {
    setBusy(true);
    try { await fn(); onChanged(); if (close) setMenu(false); }
    catch (e: any) { setMsg(e.message ?? "Could not change the clock"); }
    finally { setBusy(false); }
  };
  const goto = () => {
    if (!info || !when) return;
    const back = when < toInput(info.now);
    if (back && !confirm("Going back replays the factory from Wed 1 Apr 07:00 to this time. Chats are kept; " +
      "watches, proposals, alerts and briefings after that time are removed. Continue?")) return;
    run(async () => {
      const r = await api.goto(when);
      setMsg(r.rewound ? "Rewound and replayed." : `Moved forward (${r.boundaries} day boundaries run).`);
    }, false);
  };
  const now = state ? new Date(state.now) : null;
  const real = state?.mode === "real";
  return (
    <header className="flex h-16 shrink-0 items-center gap-2 px-3">
      <IconButton label="Menu" onClick={onMenu} className="lg:hidden"><Menu size={22} /></IconButton>
      <div className="flex items-center gap-2 whitespace-nowrap text-lg text-ink sm:text-xl">
        <Sparkle size={22} /><span>GM Co-Pilot</span>
        {state && <span className="hidden rounded-lg bg-surface-2 px-2 py-0.5 text-xs text-ink-2 sm:inline">{state.settings.model}</span>}
      </div>
      <div className="ml-auto flex shrink-0 items-center gap-1">
        <div className="relative" ref={ref}>
          <button onClick={() => setMenu(!menu)} disabled={busy} aria-label="Factory clock"
            className="flex h-9 items-center gap-2 whitespace-nowrap rounded-full bg-surface-2 px-3 text-sm text-ink-2 hover:bg-surface-3">
            {real ? <Radio size={16} className="text-good" /> : <Clock3 size={16} className={clsx(busy && "gem-spin")} />}
            <span className="hidden sm:inline">{now ? now.toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"}</span>
            <span className="sm:hidden">{now ? now.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"}</span>
            <span className={clsx("hidden text-xs sm:inline", real ? "text-good" : "text-ink-3")}>· {real ? "live" : "simulated"}</span>
          </button>
          {menu && state && (
            <div className="absolute right-0 top-11 z-30 w-[min(92vw,320px)] rounded-2xl bg-white p-2 shadow-[0_4px_16px_rgba(60,64,67,.25)]">
              <p className="px-3 py-2 text-xs text-ink-3">Scenario <b>{state.scenario}</b> · data through {state.data_through}</p>
              {real ? (
                <div className="mx-1 mb-1 rounded-xl bg-good-soft px-3 py-2 text-sm text-ink-2">
                  <p className="font-medium text-good">Running in real time</p>
                  <p className="mt-0.5">The factory clock moves at wall-clock speed from where it was. A new day of data,
                    the alerts and the briefing arrive at each 07:00
                    {info && <> — next in <b>{until(info.now, info.next_boundary)}</b> ({fmt(info.next_boundary, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })})</>}.
                    For a demo, use simulated time.</p>
                </div>
              ) : (
                [[0, 1, "Advance 1 hour"], [1, 0, "Advance 1 day (07:00)"], [2, 0, "Advance 2 days"]].map(([d, h, l]) => (
                  <button key={String(l)} onClick={() => run(() => api.advance(Number(d), Number(h)))}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-ink hover:bg-surface-2">
                    <FastForward size={16} /> {l}
                  </button>
                ))
              )}
              <div className="mx-1 mt-1 rounded-xl border border-line p-2">
                <label className="flex items-center gap-2 px-1 text-sm text-ink" htmlFor="goto-when">
                  <CalendarClock size={16} /> Go to date and time
                </label>
                <div className="mt-1.5 flex gap-1.5">
                  <input id="goto-when" type="datetime-local" value={when} min={info ? toInput(info.min) : undefined}
                    max={info ? toInput(info.max) : undefined} onChange={(e) => setWhen(e.target.value)}
                    className="h-9 min-w-0 flex-1 rounded-lg border border-line px-2 text-sm text-ink outline-none focus:border-accent" />
                  <button onClick={goto} disabled={busy || !when}
                    className="h-9 rounded-full bg-accent px-3 text-sm font-medium text-white disabled:opacity-50">Go</button>
                </div>
                <p className="mt-1.5 px-1 text-xs text-ink-3">Earlier times replay the scenario from Wed 1 Apr 07:00{real ? "; the clock switches to simulated time" : ""}.</p>
                {msg && <p className="mt-1 px-1 text-xs text-ink-2">{msg}</p>}
              </div>
              <button onClick={() => run(() => api.setMode(real ? "sim" : "real"))}
                className="mt-1 flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-ink hover:bg-surface-2">
                {real ? <Clock3 size={16} /> : <Radio size={16} />} {real ? "Back to simulated time" : "Run in real time"}
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
