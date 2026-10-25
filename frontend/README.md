# GM Co-Pilot — web app

Gemini-style chat UI for the GM Co-Pilot backend (React 19 + TypeScript + Vite + Tailwind 4).

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api to the backend on :8000
npm run build    # writes dist/, which the backend serves on the same origin
```

Set `VITE_API_BASE` at build time when the API lives on another origin (e.g. a tunnel URL).

| Area | File |
|---|---|
| Layout, view routing, polling, alert toasts | `src/App.tsx` |
| Sidebar, top bar (clock menu, alerts bell, spend) | `src/components/Shell.tsx` |
| Chat welcome, message list | `src/components/ChatView.tsx` |
| Answer card: kind, sources, proposal confirm/undo, read-aloud | `src/components/Message.tsx` |
| Live "Show thinking" steps (SSE) | `src/components/Thinking.tsx` |
| Composer with voice input (Web Speech API) | `src/components/Composer.tsx` |
| Evidence drawer (rows behind a figure) | `src/components/EvidenceDrawer.tsx` |
| Briefing, alerts, actions, watches, logs, settings | `src/views/` |
| API client and SSE parser | `src/api.ts` |
