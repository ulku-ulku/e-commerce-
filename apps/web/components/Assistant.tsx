"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Msg = { role: "user" | "assistant"; content: string; tools?: string[]; mode?: string };

const SUGGESTIONS = [
  "Ciro durumu nedir?",
  "En zararlı ürünler hangileri?",
  "Hangi kampanyayı kapatmalıyım?",
  "SKU-1004 fiyatını %10 artırırsam ne olur?",
  "Aksiyon önerin ne?",
];

export function Assistant() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([{
    role: "assistant",
    content: "Merhaba! Mağaza asistanınım. Verine bağlıyım — soru sorabilir veya aksiyon isteyebilirsin (ör. \"zararlı kampanyayı kapat\", \"SKU-1011 stok sipariş et\").",
  }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, open]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    const history = [...msgs, { role: "user" as const, content: q }];
    setMsgs(history); setInput(""); setBusy(true);
    try {
      const payload = history.filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({ role: m.role, content: m.content }));
      const res = await api.chat(payload);
      setMsgs((p) => [...p, { role: "assistant", content: res.reply,
        tools: res.tool_calls?.map((t) => t.tool), mode: res.mode }]);
    } catch {
      setMsgs((p) => [...p, { role: "assistant", content: "⚠ Bir hata oldu, tekrar dener misin?" }]);
    } finally { setBusy(false); }
  }

  return (
    <>
      {/* Açma butonu */}
      <button onClick={() => setOpen((o) => !o)}
        className="fixed bottom-5 right-5 z-40 w-14 h-14 rounded-full bg-slate-900 text-white shadow-lg hover:bg-slate-800 flex items-center justify-center text-2xl">
        {open ? "×" : "🤖"}
      </button>

      {open && (
        <div className="fixed bottom-24 right-5 z-40 w-[380px] max-w-[calc(100vw-2.5rem)] h-[540px] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col">
          {/* Başlık */}
          <div className="px-4 py-3 border-b flex items-center gap-2">
            <span className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center">🤖</span>
            <div>
              <p className="font-semibold text-sm leading-tight">Mağaza Asistanı</p>
              <p className="text-[11px] text-slate-400">verine bağlı · aksiyon alabilir</p>
            </div>
          </div>

          {/* Mesajlar */}
          <div className="flex-1 overflow-auto p-3 space-y-3">
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                  m.role === "user" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-800"}`}>
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  {m.tools && m.tools.length > 0 && (
                    <p className="text-[10px] mt-1 opacity-60">
                      🔧 {m.tools.join(", ")}{m.mode === "fallback" ? " · temel mod" : ""}
                    </p>
                  )}
                </div>
              </div>
            ))}
            {busy && <div className="text-xs text-slate-400">Asistan düşünüyor…</div>}
            <div ref={endRef} />
          </div>

          {/* Öneriler */}
          {msgs.length <= 1 && (
            <div className="px-3 pb-2 flex flex-wrap gap-1.5">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="text-[11px] border border-slate-200 rounded-full px-2.5 py-1 text-slate-600 hover:bg-slate-50">
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Giriş */}
          <form onSubmit={(e) => { e.preventDefault(); send(input); }}
            className="p-3 border-t flex items-center gap-2">
            <input value={input} onChange={(e) => setInput(e.target.value)}
              placeholder="Soru sor veya aksiyon iste…"
              className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400" />
            <button type="submit" disabled={busy}
              className="bg-slate-900 text-white text-sm px-3 py-2 rounded-lg disabled:opacity-50">↑</button>
          </form>
        </div>
      )}
    </>
  );
}
