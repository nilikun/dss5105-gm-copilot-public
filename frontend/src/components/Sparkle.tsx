import clsx from "clsx";

/** The four-point star used for the assistant (Gemini style). `spinning` while the agent works. */
export function Sparkle({ size = 28, spinning = false }: { size?: number; spinning?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden className={clsx(spinning && "gem-spin")}>
      <defs>
        <linearGradient id="gm-spark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#4285f4" />
          <stop offset="0.55" stopColor="#9b72cb" />
          <stop offset="1" stopColor="#d96570" />
        </linearGradient>
      </defs>
      <path d="M12 1c.5 5.6 5.4 10.5 11 11-5.6.5-10.5 5.4-11 11-.5-5.6-5.4-10.5-11-11 5.6-.5 10.5-5.4 11-11Z"
        fill="url(#gm-spark)" />
    </svg>
  );
}
