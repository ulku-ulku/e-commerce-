"use client";
import { useCallback, useEffect, useState } from "react";
import { api, type ActionItem, type DecisionLogItem } from "@/lib/api";

const fmt = (n: number) => Math.round(n).toLocaleString("tr-TR");
const sevBar: Record<string, string> = {
  critical: "border-l-red-500", warning: "border-l-amber-500", info: "border-l-green-500",
};
const effortLabel: Record<string, string> = { low: "kolay", med: "orta", high: "zor" };
const confStyle: Record<string, string> = {
  high: "bg-emerald-100 text-emerald-700", med: "bg-amber-100 text-amber-700",
  low: "bg-red-100 text-red-700",
};
const confLabel: Record<string, string> = { high: "yüksek güven", med: "orta güven", low: "düşük güven" };
const statusLabel: Record<string, { t: string; c: string }> = {
  executed: { t: "uygulandı", c: "text-emerald-600" },
  planned: { t: "planlandı", c: "text-blue-600" },
  applied: { t: "kaydedildi", c: "text-slate-500" },
  measured: { t: "ölçüldü", c: "text-indigo-600" },
};

export function StrategyBoard() {
  const [summary, setSummary] = useState<{ total_opportunity: number; action_count: number; low_confidence: number } | null>(null);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [log, setLog] = useState<DecisionLogItem[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [q, d] = await Promise.all([api.actionQueue(), api.decisionLog()]);
    setSummary(q.summary);
    setActions(Array.isArray(q.actions) ? q.actions : []);
    setLog(Array.isArray(d) ? d : []);
  }, []);
  useEffect(() => { load().catch(() => {}); }, [load]);

  async function execute(a: ActionItem) {
    setBusy(a.id); setToast(null);
    try {
      let res = await api.executeAction(a, false);
      if (res.needs_confirm) {
        if (!window.confirm(`${res.preview}\n\nGerçekten uygulansın mı?`)) { setBusy(null); return; }
        res = await api.executeAction(a, true);
      }
      setToast((res.change ? "✓ " + res.change : "✓ Uygulandı"));
      await load();
    } catch (e) {
      setToast("⚠ " + (e instanceof Error ? e.message : "Hata"));
    } finally { setBusy(null); }
  }
  async function measure(id: number) {
    setBusy(-id);
    try { await api.measureDecision(id); await load(); } finally { setBusy(null); }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
      <h3 className="font-semibold mb-1">🎯 Aksiyon Kuyruğu — Şimdi Ne Yapmalı?</h3>
      <p className="text-xs text-slate-400 mb-4">
        Tüm domain'ler tek listede, aylık ₺ etkisine göre sıralı · her aksiyon güven skoru + tek tık uygulama
      </p>

      {summary && (
        <div className="mb-3 bg-indigo-50 border border-indigo-200 rounded-lg p-3 flex flex-wrap items-baseline gap-x-3">
          <span className="text-2xl font-bold text-indigo-700">{fmt(summary.total_opportunity)}₺</span>
          <span className="text-sm text-indigo-600">toplam aylık fırsat · {summary.action_count} aksiyon</span>
          {summary.low_confidence > 0 && (
            <span className="text-xs text-red-600">· {summary.low_confidence} düşük güvenli</span>)}
        </div>
      )}

      {toast && (
        <div className={`mb-3 text-sm rounded-lg px-3 py-2 ${
          toast.startsWith("⚠") ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}>{toast}</div>
      )}

      <div className="grid lg:grid-cols-2 gap-5">
        {/* Aksiyon listesi */}
        <div className="space-y-2 max-h-[440px] overflow-auto">
          {actions.map((a) => (
            <div key={a.id} className={`border-l-4 ${sevBar[a.severity]} bg-slate-50 rounded-r-lg p-3`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{a.title}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{a.detail}</p>
                  <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                    <span className="text-xs bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded">{a.domain}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${confStyle[a.confidence.level]}`}>
                      {confLabel[a.confidence.level]} · {a.confidence.data_points} veri
                    </span>
                    <span className="text-xs text-slate-400">çaba: {effortLabel[a.effort]}</span>
                    {!a.exec.auto && <span className="text-xs text-blue-500">manuel</span>}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm font-bold text-green-700">+{fmt(a.impact_monthly)}₺</p>
                  <button onClick={() => execute(a)} disabled={busy === a.id}
                    className="mt-1 text-xs bg-slate-900 text-white px-2.5 py-1 rounded disabled:opacity-50">
                    {busy === a.id ? "…" : a.exec.auto ? "Uygula" : "Planla"}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Karar günlüğü (geri-besleme + audit) */}
        <div>
          <p className="text-sm font-medium text-slate-600 mb-2">Karar Günlüğü (uygulama + sonuç)</p>
          {log.length === 0 && <p className="text-xs text-slate-400">Henüz aksiyon yok. Soldan "Uygula"ya bas.</p>}
          <div className="space-y-2 max-h-[440px] overflow-auto">
            {(Array.isArray(log) ? log : []).map((r) => {
              const st = statusLabel[r.status] || statusLabel.applied;
              return (
                <div key={r.id} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium">{r.title}</p>
                    <span className={`text-xs font-medium shrink-0 ${st.c}`}>{st.t}</span>
                  </div>
                  {r.change_note && <p className="text-xs text-slate-500 mt-0.5">↳ {r.change_note}</p>}
                  <div className="flex items-center justify-between mt-1.5">
                    <span className="text-xs text-slate-400">{r.domain} · tahmini +{fmt(r.impact_estimate)}₺</span>
                    {r.status !== "measured" ? (
                      <button onClick={() => measure(r.id)} disabled={busy === -r.id}
                        className="text-xs border px-2 py-0.5 rounded disabled:opacity-50">
                        {busy === -r.id ? "…" : "Sonucu Ölç"}
                      </button>
                    ) : (
                      <span className={`text-xs font-medium ${(r.delta ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                        Gerçek etki: {r.delta! >= 0 ? "+" : ""}{fmt(r.delta!)}₺
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
