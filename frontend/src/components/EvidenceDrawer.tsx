import { Database, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Evidence } from "../types";
import { Badge, IconButton } from "./ui";

/** Right-hand sheet: the rows behind a number ("one click to the source"). */
export function EvidenceDrawer({ id, onClose }: { id: string | null; onClose: () => void }) {
  const [ev, setEv] = useState<Evidence | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setEv(null); setErr(null);
    if (id) api.evidence(id).then(setEv).catch((e) => setErr(e.message));
  }, [id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!id) return null;
  const rows = ev?.rows ?? [];
  const cols = rows.length ? Object.keys(rows[0]).filter((c) => typeof rows[0][c] !== "object" || rows[0][c] === null) : [];
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/20" onClick={onClose}>
      <aside onClick={(e) => e.stopPropagation()} aria-label="Evidence"
        className="flex h-full w-full max-w-2xl flex-col bg-white shadow-2xl sm:rounded-l-3xl">
        <header className="flex items-center gap-3 border-b border-line px-5 py-4">
          <Database size={20} className="text-accent" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 font-medium text-ink">Evidence {id} {ev && <Badge>{ev.source}</Badge>}</div>
            {ev && <p className="truncate text-sm text-ink-3">{ev.description} · recorded {ev.as_of.replace("T", " ")}</p>}
          </div>
          <IconButton label="Close" onClick={onClose}><X size={20} /></IconButton>
        </header>
        <div className="flex-1 overflow-auto p-5">
          {err && <p className="text-sm text-bad">{err}</p>}
          {!ev && !err && <p className="gem-shimmer text-sm">Loading rows…</p>}
          {ev && rows.length === 0 && <p className="text-sm text-ink-3">No rows.</p>}
          {ev && rows.length > 0 && cols.length > 0 && (
            <>
              <p className="mb-3 text-sm text-ink-2">{rows.length} row{rows.length === 1 ? "" : "s"} from the data behind this figure.</p>
              <div className="overflow-x-auto rounded-2xl border border-line">
                <table className="w-full text-left text-[13px]">
                  <thead className="bg-surface-2 text-ink-2">
                    <tr>{cols.map((c) => <th key={c} className="whitespace-nowrap px-3 py-2 font-medium">{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {rows.slice(0, 300).map((r, i) => (
                      <tr key={i} className="border-t border-line">
                        {cols.map((c) => <td key={c} className="whitespace-nowrap px-3 py-1.5 font-mono text-[12.5px] text-ink">{String(r[c] ?? "")}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {ev && rows.length > 0 && cols.length === 0 && (
            <pre className="overflow-auto rounded-2xl bg-surface-2 p-4 font-mono text-xs">{JSON.stringify(rows, null, 2)}</pre>
          )}
        </div>
      </aside>
    </div>
  );
}
