"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api, getToken, logout,
  type ForecastPoint, type Insight, type Kpi, type Source, type TimePoint,
} from "@/lib/api";
import { KpiCard } from "@/components/KpiCard";
import { RevenueChart } from "@/components/RevenueChart";
import { InsightPanel } from "@/components/InsightPanel";
import { SourcesBar } from "@/components/SourcesBar";
import { DecisionTable } from "@/components/DecisionTable";
import { AdTable } from "@/components/AdTable";
import { CustomerPanel } from "@/components/CustomerPanel";
import { FunnelChart } from "@/components/FunnelChart";
import { StrategyBoard } from "@/components/StrategyBoard";
import { PricingTable } from "@/components/PricingTable";
import { Assistant } from "@/components/Assistant";
import { GrowthPanel } from "@/components/GrowthPanel";

export default function Dashboard() {
  const router = useRouter();
  const [kpi, setKpi] = useState<Kpi | null>(null);
  const [series, setSeries] = useState<TimePoint[]>([]);
  const [forecast, setForecast] = useState<ForecastPoint[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [generating, setGenerating] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [live, setLive] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function loadAll() {
    const [k, s, f, i, src] = await Promise.all([
      api.kpi(), api.timeseries(), api.forecast(), api.insights(), api.sources(),
    ]);
    setKpi(k); setSeries(s); setForecast(f); setInsights(i); setSources(src);
  }

  async function onSync(kind: string) {
    const r = await api.connectAndSync(kind);
    await loadAll();
    return `${kind}: ${r.rows_ingested} günlük kayıt çekildi`;
  }

  async function onSyncAll(region?: string) {
    const r = await api.connectAll(region);
    await loadAll();
    return `${r.total_sources} kaynak güncellendi · ${r.rows} kayıt çekildi`;
  }

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    loadAll().catch(() => router.push("/login"));
    api.autoSyncStatus().then((s) => setLive(s.enabled)).catch(() => {});
  }, [router]);

  // Canlı mod: sunucuda otomatik senkron açıkken paneli düzenli tazele ("anlık")
  useEffect(() => {
    if (!live) return;
    const id = setInterval(() => { loadAll().catch(() => {}); }, 20000);
    return () => clearInterval(id);
  }, [live]);

  async function toggleLive() {
    const next = !live;
    setLive(next);
    await api.setAutoSync(next, 1).catch(() => {});
    if (next) loadAll().catch(() => {});
  }

  async function onGenerate() {
    setGenerating(true);
    try {
      const ins = await api.generateInsight();
      setInsights((prev) => [ins, ...prev]);
    } finally {
      setGenerating(false);
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadMsg({ ok: true, text: `"${file.name}" yükleniyor…` });
    try {
      const r = await api.uploadCsv(file);
      await loadAll();
      setUploadMsg({ ok: true, text: `✓ "${file.name}" — ${r.summary || `${r.rows_ingested} satır işlendi`}` });
    } catch (err) {
      setUploadMsg({ ok: false, text: "⚠ " + (err instanceof Error ? err.message : "Yükleme başarısız") });
    } finally {
      if (fileRef.current) fileRef.current.value = "";  // aynı dosyayı tekrar seçebilmek için
    }
  }

  const fmt = (n: number) => n.toLocaleString("tr-TR");

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-lg font-bold">Commerce-AI · Dashboard</h1>
          <div className="flex items-center gap-3">
            <button onClick={toggleLive}
              className={`text-sm px-3 py-1.5 rounded-lg border flex items-center gap-1.5 ${
                live ? "border-emerald-300 bg-emerald-50 text-emerald-700" : "text-slate-500"}`}>
              <span className={`w-2 h-2 rounded-full ${live ? "bg-emerald-500 animate-pulse" : "bg-slate-300"}`} />
              {live ? "Canlı" : "Canlı Değil"}
            </button>
            <input ref={fileRef} type="file" accept=".csv,.xlsx,.xlsm,.xls" onChange={onUpload} className="hidden" />
            <button onClick={() => fileRef.current?.click()}
              className="text-sm border px-3 py-1.5 rounded-lg">Veri Yükle (CSV/Excel)</button>
            <button onClick={() => { logout(); router.push("/login"); }}
              className="text-sm text-slate-500">Çıkış</button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {uploadMsg && (
          <div className={`text-sm rounded-lg px-4 py-2 ${
            uploadMsg.ok ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
            {uploadMsg.text}
            {!uploadMsg.ok && (
              <span className="block text-xs mt-1 opacity-80">
                CSV'de en az <b>tarih</b> (veya day) ve <b>ciro</b> (veya revenue) sütunları olmalı.
                Opsiyonel: sipariş, oturum, reklam, kanal. Ayraç , veya ; olabilir.
              </span>
            )}
          </div>
        )}

        <SourcesBar sources={sources} onSync={onSync} onSyncAll={onSyncAll} />

        {kpi && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard label="Ciro (30g)" value={fmt(kpi.revenue)} suffix="₺" delta={kpi.revenue_delta_pct} />
            <KpiCard label="Sipariş" value={fmt(kpi.orders)} />
            <KpiCard label="AOV" value={fmt(kpi.aov)} suffix="₺" />
            <KpiCard label="Dönüşüm" value={`%${kpi.conversion_rate}`} />
            <KpiCard label="ROAS" value={`${kpi.roas}x`} />
            <KpiCard label="Reklam Harc." value={fmt(kpi.ad_spend)} suffix="₺" />
            <KpiCard label="Oturum" value={fmt(kpi.sessions)} />
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <RevenueChart series={series} forecast={forecast} />
          </div>
          <InsightPanel insights={insights} onGenerate={onGenerate} generating={generating} />
        </div>

        <StrategyBoard />

        <GrowthPanel />

        <DecisionTable />

        <PricingTable />

        <div className="grid lg:grid-cols-2 gap-6">
          <FunnelChart />
          <CustomerPanel />
        </div>

        <AdTable />
      </main>

      <Assistant />
    </div>
  );
}
