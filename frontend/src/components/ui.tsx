import clsx from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Button({ variant = "tonal", className, ...p }: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "filled" | "tonal" | "text" | "outline" | "danger";
}) {
  return (
    <button
      {...p}
      className={clsx(
        "inline-flex items-center justify-center gap-1.5 rounded-full px-4 h-9 text-sm font-medium transition-colors",
        "disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent",
        variant === "filled" && "bg-accent text-white hover:bg-[#0842a0]",
        variant === "tonal" && "bg-accent-soft text-[#041e49] hover:bg-[#c2d7fb]",
        variant === "text" && "text-accent hover:bg-accent-soft/60",
        variant === "outline" && "border border-line text-ink-2 hover:bg-surface-2",
        variant === "danger" && "text-bad hover:bg-bad-soft",
        className,
      )}
    />
  );
}

export function IconButton({ label, className, children, ...p }: ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string; children: ReactNode;
}) {
  return (
    <button {...p} aria-label={label} title={label}
      className={clsx("inline-flex size-10 items-center justify-center rounded-full text-ink-2 hover:bg-surface-3",
        "disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-accent", className)}>
      {children}
    </button>
  );
}

export function Chip({ children, onClick, active, className }: { children: ReactNode; onClick?: () => void;
  active?: boolean; className?: string }) {
  const Tag = onClick ? "button" : "span";
  return (
    <Tag onClick={onClick}
      className={clsx("inline-flex items-center gap-1 rounded-lg border px-3 py-1.5 text-sm",
        active ? "border-accent bg-accent-soft text-[#041e49]" : "border-line text-ink-2",
        onClick && "hover:bg-surface-2 cursor-pointer", className)}>
      {children}
    </Tag>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "good" | "warn" | "bad" | "accent";
  children: ReactNode }) {
  return (
    <span className={clsx("inline-flex items-center rounded-md px-1.5 py-0.5 text-xs font-medium",
      tone === "neutral" && "bg-surface-3 text-ink-2", tone === "good" && "bg-good-soft text-good",
      tone === "warn" && "bg-warn-soft text-warn", tone === "bad" && "bg-bad-soft text-bad",
      tone === "accent" && "bg-accent-soft text-[#041e49]")}>
      {children}
    </span>
  );
}

export function EvidenceChip({ id, onOpen }: { id: string; onOpen: (id: string) => void }) {
  return (
    <button onClick={() => onOpen(id)} title="Show the rows behind this"
      className="inline-flex items-center rounded-full bg-surface-2 px-2 py-0.5 font-mono text-xs text-ink-2 hover:bg-accent-soft">
      {id}
    </button>
  );
}

export function Markdown({ children }: { children: string }) {
  return <div className="prose-gm text-[15px] text-ink"><ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown></div>;
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("rounded-3xl bg-surface-2 p-5", className)}>{children}</div>;
}

export function SectionTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="text-[22px] font-normal text-ink">{children}</h2>
      {right}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-2xl border border-dashed border-line p-6 text-center text-sm text-ink-3">{children}</p>;
}

export function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}
