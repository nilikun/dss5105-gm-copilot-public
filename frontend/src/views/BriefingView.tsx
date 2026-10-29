import { RefreshCw, Sparkles } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import { Sparkle } from "../components/Sparkle";
import { Badge, Button, Card, EvidenceChip } from "../components/ui";
import type { Briefing, BriefingItem } from "../types";

export function BriefingView({ briefing, onReload, onEvidence, onAsk }: { briefing: Briefing | null;
  onReload: () => void; onEvidence: (id: string) => void; onAsk: (t: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  if (!briefing) return <p className="p-8 text-ink-3">Loading briefing…</p>;
  const s = briefing.structured;
  const [rebuilding, setRebuilding] = useState(false);
  const narrate = async (force = false) => {
    setBusy(true); setErr(null);
    try { await api.narrate(force); onReload(); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };
  const rebuild = async () => {
    setRebuilding(true); setErr(null);
    try { await api.rebuildBriefing(); onReload(); } catch (e: any) { setErr(e.message); } finally { setRebuilding(false); }
  };
  const Section = ({ title, items, empty }: { title: string; items: BriefingItem[]; empty: string }) => (
    <section className="mt-6">
      <h3 className="mb-2 text-sm font-medium uppercase tracking-wide text-ink-3">{title}</h3>
      {items.length === 0 ? <p className="text-sm text-ink-3">{empty}</p> : (
        <ul className="divide-y divide-line rounded-2xl border border-line">
          {items.map((i, n) => (
            <li key={n} className="flex flex-col gap-1.5 px-4 py-3 sm:flex-row sm:items-start sm:gap-3">
              <span className="flex-1 text-[15px] leading-relaxed text-ink">{i.text}</span>
              <span className="flex shrink-0 items-center gap-1.5">
                {i.type && <Badge>{i.type.replaceAll("_", " ")}</Badge>}
                {i.evidence_id && <EvidenceChip id={i.evidence_id} onOpen={onEvidence} />}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm text-ink-3">Morning briefing</p>
            <h1 className="text-3xl font-normal text-ink">{new Date(s.date).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</h1>
            <p className="mt-1 text-sm text-ink-3">Generated {briefing.created_at.replace("T", " ")} · data through {s.data_through}
              {s.suppressed_findings > 0 && ` · ${s.suppressed_findings} lower-priority findings not shown`}</p>
          </div>
          <Button variant="outline" onClick={rebuild} disabled={rebuilding}
            title="Rebuild today's briefing from the current data (the written summary is cleared)">
            <RefreshCw size={16} className={rebuilding ? "gem-spin" : undefined} /> {rebuilding ? "Rebuilding…" : "Refresh"}
          </Button>
        </div>

        <Card className="mt-6">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-ink-2"><Sparkle size={18} /> Summary</div>
          {briefing.narrative ? (
            <div>
              <p className="whitespace-pre-line text-[16px] leading-relaxed text-ink">{briefing.narrative}</p>
              <Button variant="text" className="mt-2 -ml-3" disabled={busy} onClick={() => narrate(true)}>
                <Sparkles size={16} /> {busy ? "Rewriting…" : "Rewrite summary"}
              </Button>
              {err && <p className="mt-2 text-sm text-bad">{err}</p>}
            </div>
          ) : (
            <div>
              <p className="text-[15px] text-ink-2">
                {briefing.narrative_status === "pending" ? "The structured briefing below is ready. A short written summary can be generated from it — every figure is checked against the briefing data."
                  : briefing.narrative_status === "rejected" ? "The written summary was rejected because it stated a figure not in the briefing data; the structured briefing below stands."
                    : "The written summary is unavailable; the structured briefing below stands."}
              </p>
              <Button variant="tonal" className="mt-3" disabled={busy} onClick={() => narrate()}>
                <Sparkles size={16} /> {busy ? "Writing…" : "Write summary"}
              </Button>
              {err && <p className="mt-2 text-sm text-bad">{err}</p>}
            </div>
          )}
        </Card>

        <Section title="Yesterday" items={s.yesterday} empty="Nothing unusual recorded." />
        <Section title="At risk" items={s.at_risk} empty="No exceptions found." />
        <Section title="Decisions today" items={s.decisions} empty="No decisions waiting." />

        <div className="mt-8 flex flex-wrap gap-2">
          {["Why is ASSEMBLY flagged?", "Which orders are likely late this week?", "Show me the overdue orders"].map((q) => (
            <button key={q} onClick={() => onAsk(q)} className="rounded-full border border-line px-3 py-1.5 text-sm text-ink-2 hover:bg-surface-2">{q}</button>
          ))}
        </div>
      </div>
    </div>
  );
}
