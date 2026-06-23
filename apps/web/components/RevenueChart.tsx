"use client";
import {
  Area, AreaChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { ForecastPoint, TimePoint } from "@/lib/api";

export function RevenueChart({ series, forecast }: { series: TimePoint[]; forecast: ForecastPoint[] }) {
  const data = [
    ...series.map((p) => ({ day: p.day.slice(5), revenue: p.revenue, predicted: null as number | null })),
    ...forecast.map((p) => ({ day: p.day.slice(5), revenue: null as number | null, predicted: p.predicted_revenue })),
  ];
  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h3 className="font-semibold mb-4">Ciro Trendi & 14 Günlük Tahmin</h3>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0f172a" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#0f172a" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="day" fontSize={11} interval={6} />
          <YAxis fontSize={11} width={50} />
          <Tooltip />
          <Area type="monotone" dataKey="revenue" stroke="#0f172a" fill="url(#rev)" name="Gerçek" />
          <Line type="monotone" dataKey="predicted" stroke="#6366f1" strokeDasharray="5 5" dot={false} name="Tahmin" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
