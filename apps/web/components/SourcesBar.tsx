"use client";
import { useEffect, useMemo, useState } from "react";
import { api, type Marketplace, type Source } from "@/lib/api";

// Marka renkleri (monogram kutucuğu için)
const BRAND: Record<string, string> = {
  trendyol: "#F27A1A", hepsiburada: "#FF6000", n11: "#FF3D00", ciceksepeti: "#E6007E",
  pazarama: "#6C2BD9", pttavm: "#00529C", amazon_tr: "#FF9900", shopify: "#5E8E3E",
  amazon: "#FF9900", ebay: "#E53238", etsy: "#F45800", aliexpress: "#E62E04",
  walmart: "#0071CE", allegro: "#FF5A00", cdiscount: "#D50000", noon: "#C9A700", ozon: "#005BFF",
};

function monogram(label: string): string {
  const words = label.replace(/[()]/g, "").trim().split(/\s+/);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return label.slice(0, 2);
}

type Filter = "all" | "tr" | "global";

export function SourcesBar({
  sources, onSync, onSyncAll,
}: {
  sources: Source[];
  onSync: (kind: string) => Promise<string>;
  onSyncAll: (region?: string) => Promise<string>;
}) {
  const [catalog, setCatalog] = useState<Marketplace[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");

  useEffect(() => { api.catalog().then((d) => setCatalog(d.marketplaces)).catch(() => {}); }, []);

  const srcMap = useMemo(() => {
    const m: Record<string, Source> = {};
    sources.forEach((s) => { m[s.kind] = s; });
    return m;
  }, [sources]);

  const connectedCount = catalog.filter((m) => srcMap[m.key]?.status === "connected").length;
  const shown = catalog.filter((m) => filter === "all" || m.region === filter);

  async function run(id: string, fn: () => Promise<string>) {
    setBusy(id); setMsg(null);
    try { setMsg("✓ " + await fn()); }
    catch (e) { setMsg("⚠ " + (e instanceof Error ? e.message : "Hata")); }
    finally { setBusy(null); }
  }

  const tabs: { id: Filter; label: string }[] = [
    { id: "all", label: "Tümü" },
    { id: "tr", label: "🇹🇷 Yurt İçi" },
    { id: "global", label: "🌍 Global" },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-4">
      {/* Başlık */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-baseline gap-2">
          <h3 className="font-semibold text-slate-900 text-sm">Veri Kaynakları</h3>
          <span className="text-xs text-slate-400">{connectedCount}/{catalog.length} bağlı</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Filtre sekmeleri */}
          <div className="flex items-center gap-0.5 bg-slate-100 rounded-md p-0.5">
            {tabs.map((t) => (
              <button key={t.id} onClick={() => setFilter(t.id)}
                className={`text-xs px-2 py-1 rounded transition ${
                  filter === t.id ? "bg-white shadow-sm font-medium text-slate-900" : "text-slate-500 hover:text-slate-700"}`}>
                {t.label}
              </button>
            ))}
          </div>
          <button onClick={() => run("all-sync", () => onSyncAll(filter === "all" ? undefined : filter))}
            disabled={busy === "all-sync"}
            className="text-xs bg-slate-900 text-white px-3 py-1.5 rounded-md font-medium hover:bg-slate-800 transition disabled:opacity-50">
            {busy === "all-sync" ? "…" : "Senkronize Et"}
          </button>
        </div>
      </div>

      {msg && (
        <div className={`mb-3 text-xs rounded-md px-2.5 py-1.5 ${
          msg.startsWith("⚠") ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}>
          {msg}
        </div>
      )}

      {/* Kompakt kart ızgarası */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
        {shown.map((m) => {
          const s = srcMap[m.key];
          const connected = s?.status === "connected";
          const color = BRAND[m.key] || "#64748B";
          return (
            <button key={m.key} onClick={() => run(m.key, () => onSync(m.key))} disabled={busy === m.key}
              title={connected ? "Yenile" : "Bağla"}
              className={`group flex items-center gap-2 rounded-lg border px-2.5 py-2 text-left transition disabled:opacity-50 ${
                connected ? "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm"
                          : "border-dashed border-slate-200 bg-slate-50/60 hover:bg-white"}`}>
              <div className="relative shrink-0">
                <div className="w-8 h-8 rounded-md flex items-center justify-center text-white font-bold text-[11px]"
                  style={{ backgroundColor: color }}>
                  {monogram(m.label)}
                </div>
                <span className={`absolute -right-0.5 -bottom-0.5 w-2.5 h-2.5 rounded-full border-2 border-white ${
                  connected ? "bg-emerald-500" : "bg-slate-300"}`} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-900 truncate leading-tight">{m.label}</p>
                <p className="text-[10px] text-slate-400 truncate">
                  {busy === m.key ? "çekiliyor…" : connected ? "bağlı · yenile" : "bağla"}
                  {m.live_ready && <span className="text-emerald-600"> · canlı</span>}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
