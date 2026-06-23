"use client";
import { useEffect, useState } from "react";
import { api, type FunnelData } from "@/lib/api";

const fmt = (n: number) => Math.round(n).toLocaleString("tr-TR");

export function FunnelChart() {
  const [d, setD] = useState<FunnelData | null>(null);
  useEffect(() => { api.funnel().then(setD).catch(() => {}); }, []);
  if (!d) return null;

  const max = d.stages[0]?.count || 1;

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h3 className="font-semibold mb-1">Trafik & Dönüşüm Hunisi</h3>
      <p className="text-xs text-slate-400 mb-4">Darboğaz tespiti — nerede kan kaybediyoruz?</p>

      <div className="space-y-2 mb-4">
        {d.stages.map((s, i) => {
          const isBottleneck = s.label === d.summary.bottleneck_stage;
          const w = (s.count / max) * 100;
          return (
            <div key={s.key}>
              <div className="flex justify-between text-xs mb-0.5">
                <span className={isBottleneck ? "font-bold text-red-600" : "text-slate-600"}>
                  {s.label} {isBottleneck && "⚠"}
                </span>
                <span className="text-slate-400">
                  {fmt(s.count)} {i > 0 && `· ${s.step_rate}%`}
                </span>
              </div>
              <div className="bg-slate-100 rounded h-7 overflow-hidden">
                <div className={`h-7 rounded flex items-center px-2 text-xs text-white
                  ${isBottleneck ? "bg-red-500" : "bg-indigo-500"}`}
                  style={{ width: `${Math.max(w, 8)}%` }}>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-red-50 border border-red-200 rounded-lg p-3">
        <p className="text-xs text-red-700">
          <span className="font-bold">Darboğaz: {d.summary.bottleneck_stage}</span> ({d.summary.bottleneck_rate}%)
          <br />{d.summary.recommendation}
        </p>
      </div>
      <p className="text-xs text-slate-400 mt-2">
        Genel dönüşüm: %{d.summary.overall_conversion}
      </p>
    </div>
  );
}
