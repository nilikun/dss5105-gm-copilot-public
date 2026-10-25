import { useEffect, useState } from "react";
import { accessCode, api, setAccessCode } from "../api";
import { Button, Card, SectionTitle } from "../components/ui";
import type { AppState, Scenario } from "../types";

export function SettingsView({ state, onChanged }: { state: AppState | null; onChanged: () => void }) {
  const [code, setCode] = useState(accessCode());
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => { api.scenarios().then(setScenarios).catch(() => undefined); }, []);
  const s = state?.settings;
  const patch = async (body: Record<string, unknown>) => { await api.patchSettings(body as any); onChanged(); };
  const reset = async (name: string) => {
    if (!confirm(`Reset all data, chats and actions and start scenario "${name}" at Wed 1 Apr 2026 07:00?`)) return;
    await api.reset(name); setMsg(`Scenario "${name}" started.`); onChanged();
  };
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-8 sm:px-6">
        <SectionTitle>Settings</SectionTitle>
        <Card>
          <h3 className="font-medium text-ink">Access code</h3>
          <p className="mt-1 text-sm text-ink-3">Required on public deployments. Stored only in this browser.</p>
          <div className="mt-3 flex gap-2">
            <input value={code} onChange={(e) => setCode(e.target.value)} type="password" placeholder="Access code"
              className="h-10 flex-1 rounded-full border border-line bg-white px-4 text-sm outline-none focus:border-accent" />
            <Button variant="filled" onClick={() => { setAccessCode(code); setMsg("Access code saved."); onChanged(); }}>Save</Button>
          </div>
        </Card>
        {s && (
          <Card>
            <h3 className="font-medium text-ink">Answer quality</h3>
            <label className="mt-3 flex items-start gap-3 text-[15px] text-ink">
              <input type="checkbox" className="mt-1 size-4 accent-[#0b57d0]" checked={s.critic_enabled}
                onChange={(e) => patch({ critic_enabled: e.target.checked })} />
              <span>LLM reviewer (critic) — a second check after the verifier for relevance, ambiguity and honesty. Adds one model call per answer; its value is being measured (RQ2).</span>
            </label>
            <p className="mt-3 text-sm text-ink-3">Model {s.model} · reasoning {s.reasoning_effort} · daily budget ${s.daily_budget_usd.toFixed(2)}
              {state && ` · spent today $${state.usage.cost_usd.toFixed(4)} in ${state.usage.calls} calls`}</p>
          </Card>
        )}
        {s && (
          <Card>
            <h3 className="font-medium text-ink">Interruptions</h3>
            <p className="mt-1 text-sm text-ink-3">At most this many system alerts per day are pushed as P1; the rest wait for the briefing. Your own watches always come through.</p>
            <div className="mt-3 flex items-center gap-3">
              <input type="range" min={0} max={10} value={s.interrupt_cap} onChange={(e) => patch({ interrupt_cap: Number(e.target.value) })} className="flex-1 accent-[#0b57d0]" />
              <span className="w-8 text-right font-medium">{s.interrupt_cap}</span>
            </div>
          </Card>
        )}
        <Card>
          <h3 className="font-medium text-ink">Simulation scenarios</h3>
          <p className="mt-1 text-sm text-ink-3">The data stops on 31 Mar 2026. Scenarios generate the following days reproducibly, so watches and alerts can fire. Starting one resets everything.</p>
          <ul className="mt-3 space-y-2">
            {scenarios.map((sc) => (
              <li key={sc.name} className="flex items-start gap-3 rounded-2xl bg-white p-3">
                <div className="flex-1">
                  <p className="font-medium text-ink">{sc.title} {state?.scenario === sc.name && <span className="text-sm text-accent">· running</span>}</p>
                  <p className="text-sm text-ink-3">{sc.description}</p>
                </div>
                <Button variant="outline" onClick={() => reset(sc.name)}>Start</Button>
              </li>
            ))}
          </ul>
        </Card>
        {msg && <p className="text-sm text-good">{msg}</p>}
      </div>
    </div>
  );
}
