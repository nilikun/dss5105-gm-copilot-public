import clsx from "clsx";
import { ArrowUp, Mic, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { IconButton } from "./ui";

// Web Speech API (Chrome / Edge expose the prefixed constructor).
const SpeechRecognitionCtor: any =
  typeof window !== "undefined" ? (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition : null;

export function Composer({ onSend, disabled, placeholder }: { onSend: (text: string) => void; disabled: boolean;
  placeholder?: string }) {
  const [text, setText] = useState("");
  const [listening, setListening] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);
  const rec = useRef<any>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }, [text]);

  const send = () => {
    const t = text.trim();
    if (!t || disabled) return;
    onSend(t);
    setText("");
  };

  const toggleMic = () => {
    if (!SpeechRecognitionCtor) return;
    if (listening) { rec.current?.stop(); return; }
    const r = new SpeechRecognitionCtor();
    r.lang = "en-US";
    r.interimResults = true;
    r.continuous = false;
    r.onresult = (e: any) => setText(Array.from(e.results).map((x: any) => x[0].transcript).join(""));
    r.onend = () => setListening(false);
    r.onerror = () => setListening(false);
    rec.current = r;
    setListening(true);
    r.start();
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-3 pb-3 sm:px-4">
      <div className={clsx("flex items-end gap-1 rounded-[28px] bg-surface-2 py-2 pl-5 pr-2 transition-shadow",
        "focus-within:bg-white focus-within:shadow-[0_1px_6px_rgba(60,64,67,.24)]")}>
        <textarea ref={ref} rows={1} value={text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          placeholder={placeholder ?? "Ask GM Co-Pilot"} aria-label="Message"
          className="max-h-[200px] flex-1 resize-none bg-transparent py-2 text-base text-ink outline-none placeholder:text-ink-3" />
        {SpeechRecognitionCtor && (
          <IconButton label={listening ? "Stop listening" : "Speak"} onClick={toggleMic}
            className={clsx(listening && "bg-bad-soft text-bad")}>
            {listening ? <Square size={18} /> : <Mic size={20} />}
          </IconButton>
        )}
        <IconButton label="Send" onClick={send} disabled={disabled || !text.trim()}
          className={clsx(text.trim() && !disabled && "bg-accent text-white hover:bg-[#0842a0]")}>
          <ArrowUp size={20} />
        </IconButton>
      </div>
      <p className="mt-2 text-center text-xs text-ink-3">
        Every figure is checked against the factory data before it is shown. Actions only happen after you confirm.
      </p>
    </div>
  );
}
