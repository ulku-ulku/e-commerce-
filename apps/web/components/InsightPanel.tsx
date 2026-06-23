"use client";
import type { Insight } from "@/lib/api";

const sevColor: Record<string, string> = {
  info: "bg-blue-50 border-blue-200 text-blue-800",
  warning: "bg-amber-50 border-amber-200 text-amber-800",
  critical: "bg-red-50 border-red-200 text-red-800",
};

export function InsightPanel({
  insights, onGenerate, generating,
}: { insights: Insight[]; onGenerate: () => void; generating: boolean }) {
  return (
    <div className="bg-white rounded-xl shadow p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">AI İçgörüler & Öneriler</h3>
        <button onClick={onGenerate} disabled={generating}
          className="text-sm bg-indigo-600 text-white px-3 py-1.5 rounded-lg disabled:opacity-50">
          {generating ? "Üretiliyor…" : "✨ Yeni İçgörü Üret"}
        </button>
      </div>
      <div className="space-y-3 max-h-[420px] overflow-auto">
        {insights.length === 0 && (
          <p className="text-sm text-slate-400">Henüz içgörü yok. "Yeni İçgörü Üret"e bas.</p>
        )}
        {insights.map((i) => (
          <div key={i.id} className={`border rounded-lg p-4 ${sevColor[i.severity] || sevColor.info}`}>
            <p className="font-medium">{i.title}</p>
            <p className="text-sm mt-1 opacity-90">{i.body}</p>
            {i.actions.length > 0 && (
              <ul className="mt-2 space-y-1">
                {i.actions.map((a, idx) => (
                  <li key={idx} className="text-sm">
                    <span className="font-medium">→ {a.title}</span>
                    <span className="ml-1 text-xs opacity-70">[{a.impact}]</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
