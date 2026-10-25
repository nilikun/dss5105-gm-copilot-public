import { useCallback, useEffect, useRef, useState } from "react";
import { api, chatStream } from "./api";
import { ChatView } from "./components/ChatView";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import type { ChatItem } from "./components/Message";
import { Sidebar, TopBar, type View } from "./components/Shell";
import type { AppState, Briefing, Conversation, Reply, StoredMessage } from "./types";
import { BriefingView } from "./views/BriefingView";
import { ActionsView, AlertsView, LogsView, WatchesView } from "./views/ListViews";
import { SettingsView } from "./views/SettingsView";

let seq = 0;
const nextId = () => `m${++seq}`;

function fromStored(messages: StoredMessage[]): ChatItem[] {
  return messages.map((m) => m.role === "user"
    ? { id: nextId(), role: "user" as const, text: m.content.text }
    : { id: nextId(), role: "assistant" as const, running: false, steps: [], reply: { ...m.content, tool_calls: [] } as Reply });
}

export default function App() {
  const [view, setView] = useState<View>("chat");
  const [sidebar, setSidebar] = useState(() => window.innerWidth >= 1024);
  const [state, setState] = useState<AppState | null>(null);
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [items, setItems] = useState<ChatItem[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [running, setRunning] = useState(false);
  const [evidence, setEvidence] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [offline, setOffline] = useState<string | null>(null);
  const lastP1 = useRef<number | null>(null);  // null until the first poll: no toast for alerts already waiting

  const refresh = useCallback(async () => {
    try {
      const s = await api.state();
      setState(s); setOffline(null);
      if (lastP1.current !== null && s.unread_p1 > lastP1.current) {
        const n = (await api.notifications()).find((x) => x.priority === "P1" && !x.read);
        if (n) setToast(`${n.title} — ${n.body}`);
      }
      lastP1.current = s.unread_p1;
      setBriefing(await api.briefing());
      setConversations(await api.conversations());
    } catch (e: any) {
      setOffline(e.status === 401 ? "Access code required — open Settings." : "Cannot reach the server.");
    }
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 10000); return () => clearInterval(t); }, [refresh]);
  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 8000); return () => clearTimeout(t); } }, [toast]);

  const send = useCallback(async (text: string) => {
    if (running) return;
    setView("chat");
    const uid = nextId(), aid = nextId();
    setItems((xs) => [...xs, { id: uid, role: "user", text }, { id: aid, role: "assistant", running: true, steps: [] }]);
    setRunning(true);
    const patch = (fn: (a: Extract<ChatItem, { role: "assistant" }>) => Partial<Extract<ChatItem, { role: "assistant" }>>) =>
      setItems((xs) => xs.map((x) => (x.id === aid && x.role === "assistant" ? { ...x, ...fn(x) } : x)));
    await chatStream(text, conversationId, {
      onStep: (e) => patch((a) => ({ steps: [...a.steps, e] })),
      onReply: (r) => { patch(() => ({ reply: r, running: false })); setConversationId(r.conversation_id); },
      onError: (m) => patch(() => ({ error: m, running: false })),
    });
    patch(() => ({ running: false }));
    setRunning(false);
    refresh();
  }, [conversationId, running, refresh]);

  const newChat = () => { setItems([]); setConversationId(null); };
  const openConv = async (id: string) => { setItems(fromStored(await api.conversation(id))); setConversationId(id); };

  return (
    <div className="flex h-full overflow-hidden bg-surface">
      <Sidebar open={sidebar} setOpen={setSidebar} view={view} setView={setView} state={state}
        conversations={conversations} activeConv={conversationId} onNewChat={newChat} onOpenConv={openConv} />
      <main className="flex min-w-0 flex-1 flex-col">
        <TopBar state={state} onMenu={() => setSidebar(true)} onChanged={refresh} onAlerts={() => setView("alerts")} />
        {offline && <div className="mx-4 mb-2 rounded-2xl bg-warn-soft px-4 py-2 text-sm text-warn">{offline}</div>}
        <div className="min-h-0 flex-1">
          {view === "chat" && <ChatView items={items} running={running} onSend={send} onEvidence={setEvidence}
            onChanged={refresh} state={state} briefing={briefing} openBriefing={() => setView("briefing")} />}
          {view === "briefing" && <BriefingView briefing={briefing} onReload={refresh} onEvidence={setEvidence} onAsk={send} />}
          {view === "alerts" && <AlertsView onEvidence={setEvidence} onChanged={refresh} />}
          {view === "actions" && <ActionsView onChanged={refresh} />}
          {view === "watches" && <WatchesView />}
          {view === "logs" && <LogsView />}
          {view === "settings" && <SettingsView state={state} onChanged={refresh} />}
        </div>
      </main>
      <EvidenceDrawer id={evidence} onClose={() => setEvidence(null)} />
      {toast && (
        <div role="status" onClick={() => { setToast(null); setView("alerts"); }}
          className="fixed bottom-24 left-1/2 z-50 w-[min(92vw,560px)] -translate-x-1/2 cursor-pointer rounded-2xl bg-[#1f1f1f] px-5 py-3 text-sm text-white shadow-xl">
          <b>Alert</b> · {toast}
        </div>
      )}
    </div>
  );
}
