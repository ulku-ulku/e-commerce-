"use client";
import { useEffect, useState } from "react";
import { api, type AdSummary, type Campaign } from "@/lib/api";

const sevDot: Record<string, string> = {
  critical: "bg-red-500", warning: "bg-amber-500", info: "bg-green-500",
};
const fmt = (n: number) => Math.round(n).toLocaleString("tr-TR");

export function AdTable() {
  const [summary, setSummary] = useState<AdSummary | null>(null);
  const [items, setItems] = useState<Campaign[]>([]);

  useEffect(() => {
    api.ads().then((d) => { setSummary(d.summary); setItems(d.items); }).catch(() => {});
  }, []);

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h3 className="font-semibold mb-1">Reklam Motoru — ROAS / CAC / Payback</h3>
      <p className="text-xs text-slate-400 mb-4">Kampanya başına verim + "kapat/ölçekle" kararı</p>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <Stat label="Blended ROAS" value={`${summary.blended_roas}x`}
            tone={summary.blended_roas >= 2 ? "good" : "bad"} />
          <Stat label="Toplam Harcama" value={`${fmt(summary.total_spend)}₺`} tone="neutral" />
          <Stat label="Kapatılacak" value={`${summary.campaigns_to_cut}`}
            tone={summary.campaigns_to_cut ? "bad" : "good"} />
          <Stat label="Ort. LTV" value={`${fmt(summary.avg_ltv)}₺`} tone="neutral" />
        </div>
      )}

      <div className="overflow-auto max-h-[360px]">
        <table className="w-full text-sm">
          <thead className="text-left text-slate-400 text-xs sticky top-0 bg-white">
            <tr>
              <th className="py-2 pr-2">Kampanya</th>
              <th className="py-2 px-2 text-right">Harcama</th>
              <th className="py-2 px-2 text-right">ROAS</th>
              <th className="py-2 px-2 text-right">CAC</th>
              <th className="py-2 pl-2">Karar</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id} className="border-t hover:bg-slate-50">
                <td className="py-2 pr-2">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${sevDot[c.severity]}`} />
                    <span className="font-medium">{c.name}</span>
                    <span className="text-xs text-slate-400">{c.platform}</span>
                  </div>
                </td>
                <td className="py-2 px-2 text-right">{fmt(c.spend)}₺</td>
                <td className={`py-2 px-2 text-right font-bold ${c.roas >= 2 ? "text-green-600" : "text-red-600"}`}>
                  {c.roas}x
                </td>
                <td className="py-2 px-2 text-right">{c.cac ? `${fmt(c.cac)}₺` : "—"}</td>
                <td className="py-2 pl-2 text-xs text-slate-600 max-w-[240px]">{c.recommendation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone: "good" | "bad" | "neutral" }) {
  const c = tone === "good" ? "text-green-600" : tone === "bad" ? "text-red-600" : "text-slate-700";
  return (
    <div className="border rounded-lg p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-lg font-bold ${c}`}>{value}</p>
    </div>
  );
}
