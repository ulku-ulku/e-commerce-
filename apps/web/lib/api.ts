const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

function authHeaders(): HeadersInit {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error("Giriş başarısız");
  const data = await res.json();
  localStorage.setItem("token", data.access_token);
  return data.access_token;
}

export function logout() {
  localStorage.removeItem("token");
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json();
}

export type Kpi = {
  revenue: number; orders: number; sessions: number; ad_spend: number;
  aov: number; conversion_rate: number; roas: number; revenue_delta_pct: number;
};
export type TimePoint = { day: string; revenue: number; orders: number };
export type ForecastPoint = { day: string; predicted_revenue: number };
export type Insight = {
  id: number; title: string; body: string; severity: string;
  actions: { title: string; impact: string; why: string }[]; created_at: string;
};

export type Source = {
  id: number; kind: string; mode: string; status: string; last_synced_at: string | null;
};
export type Marketplace = {
  key: string; label: string; region: string; country: string;
  currency: string; live_ready: boolean;
};

export type SkuDecision = {
  sku: string; category: string; units: number; net_sales: number;
  profit: number; margin: number; stock: number; days_of_stock: number;
  lead_time_days: number; price: number; competitor_price: number | null;
  decision_score: number; recommendation: string; severity: string;
  components: Record<string, number>;
};
export type DecisionSummary = {
  total_profit: number; avg_margin: number; loss_making_skus: number;
  stock_risk_skus: number; total_skus: number; customer_churn_pct: number;
};

export type Campaign = {
  id: number; name: string; platform: string; status: string;
  spend: number; revenue: number; roas: number; cac: number | null;
  ctr: number; cvr: number; conversions: number; new_customers: number;
  payback_orders: number | null; recommendation: string; severity: string;
};
export type AdSummary = {
  total_spend: number; total_revenue: number; blended_roas: number;
  campaigns_to_cut: number; avg_ltv: number;
};
export type CustomerOverview = {
  summary: { total_customers: number; avg_ltv: number; repeat_rate: number;
    churn_pct: number; recommendation: string };
  segments: { segment: string; count: number; ltv: number }[];
  top_customers: { external_id: string; city: string; segment: string; orders: number; ltv: number }[];
  at_risk: { external_id: string; city: string; ltv: number; last_order: string }[];
};
export type GrowthRow = { name?: string; sku?: string; current: number; previous: number; change_pct: number };
export type GrowthData = {
  summary: { period_label: string; revenue_current: number; revenue_previous: number;
    revenue_change_pct: number; orders_change_pct: number };
  channels: GrowthRow[]; categories: GrowthRow[]; top_growing: GrowthRow[]; top_shrinking: GrowthRow[];
};
export type AutoSync = { enabled: boolean; minutes: number; last_run: string | null; last_synced: number };

export type FunnelData = {
  summary: { overall_conversion: number; bottleneck_stage: string | null;
    bottleneck_rate: number | null; recommendation: string };
  stages: { key: string; label: string; count: number; step_rate: number }[];
};

export type ActionItem = {
  id: number; domain: string; title: string; detail: string;
  impact_monthly: number; effort: string; severity: string; priority: number;
  confidence: { score: number; level: string; data_points: number };
  exec: { type: string; target: string | number; params: Record<string, number>; auto: boolean };
  requires_confirm: boolean;
};
export type PricingItem = {
  sku: string; category: string; price: number; competitor_price: number | null;
  elasticity: number; units: number; current_profit: number;
  recommended_pct: number; profit_uplift: number; verdict: string;
};
export type DecisionLogItem = {
  id: number; title: string; domain: string; status: string;
  change_note: string | null;
  impact_estimate: number; baseline_value: number; outcome_value: number | null;
  delta: number | null; created_at: string;
};

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
  return res.json();
}

export const api = {
  kpi: () => get<Kpi>("/api/kpi/summary"),
  actionQueue: () => get<{ summary: { total_opportunity: number; action_count: number; low_confidence: number };
    actions: ActionItem[] }>("/api/analytics/action-queue"),
  pricing: () => get<{ summary: { total_uplift: number; actionable: number };
    items: PricingItem[] }>("/api/analytics/pricing"),
  simulate: (sku: string, pct: number) =>
    post<{ sku: string; elasticity: number; current: { profit: number };
      simulated: { units_change_pct: number; profit: number; profit_delta: number } }>(
      "/api/analytics/pricing/simulate", { sku, price_change_pct: pct }),
  decisionLog: () => get<DecisionLogItem[]>("/api/analytics/decisions"),
  applyDecision: (a: { title: string; domain: string; impact_estimate: number }) =>
    post<{ id: number }>("/api/analytics/decisions/apply", a),
  chat: (messages: { role: string; content: string }[]) =>
    post<{ reply: string; tool_calls: { tool: string }[]; mode: string }>(
      "/api/assistant/chat", { messages }),
  executeAction: (a: ActionItem, confirm: boolean) =>
    post<{ id?: number; status?: string; ok?: boolean; change?: string;
      needs_confirm?: boolean; preview?: string }>("/api/analytics/actions/execute", {
      title: a.title, domain: a.domain, impact_estimate: a.impact_monthly,
      requires_confirm: a.requires_confirm, confirm, exec: a.exec,
    }),
  measureDecision: (id: number) =>
    post<{ id: number; delta: number }>(`/api/analytics/decisions/${id}/measure`),
  decisions: () => get<{ summary: DecisionSummary; items: SkuDecision[] }>(
    "/api/analytics/decision-scores"),
  ads: () => get<{ summary: AdSummary; items: Campaign[] }>("/api/analytics/ads"),
  customers: () => get<CustomerOverview>("/api/analytics/customers"),
  funnel: () => get<FunnelData>("/api/analytics/funnel"),
  growth: (period: "week" | "month" = "week") => get<GrowthData>(`/api/analytics/growth?period=${period}`),
  autoSyncStatus: () => get<AutoSync>("/api/sources/auto-sync"),
  setAutoSync: (enabled: boolean, minutes = 1) =>
    post<AutoSync>("/api/sources/auto-sync", { enabled, minutes }),
  sources: () => get<Source[]>("/api/sources"),
  catalog: () => get<{ marketplaces: Marketplace[] }>("/api/sources/catalog"),
  connectAll: async (region?: string): Promise<{ total_sources: number; rows: number }> => {
    const res = await fetch(`${BASE}/api/sources/connect-all`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ region: region ?? null, mode: "sandbox" }),
    });
    if (!res.ok) throw new Error("Toplu bağlantı başarısız");
    const d = await res.json();
    const rows = (d.synced || []).reduce(
      (a: number, r: { rows_ingested?: number }) => a + (r.rows_ingested || 0), 0);
    return { total_sources: d.total_sources, rows };
  },
  connectAndSync: async (kind: string): Promise<{ rows_ingested: number }> => {
    const c = await fetch(`${BASE}/api/sources/connect`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ kind, mode: "sandbox" }),
    });
    if (!c.ok) throw new Error("Bağlantı başarısız");
    const src = await c.json();
    const s = await fetch(`${BASE}/api/sources/${src.id}/sync?days=30`, {
      method: "POST", headers: authHeaders(),
    });
    if (!s.ok) throw new Error("Senkron başarısız");
    return s.json();
  },
  timeseries: () => get<TimePoint[]>("/api/kpi/timeseries"),
  forecast: () => get<ForecastPoint[]>("/api/kpi/forecast"),
  insights: () => get<Insight[]>("/api/insights"),
  generateInsight: async (): Promise<Insight> => {
    const res = await fetch(`${BASE}/api/insights/generate`, {
      method: "POST", headers: authHeaders(),
    });
    if (!res.ok) throw new Error("İçgörü üretilemedi");
    return res.json();
  },
  uploadCsv: async (file: File): Promise<{ rows_ingested: number; summary?: string }> => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/api/ingest/csv`, {
      method: "POST", headers: authHeaders(), body: fd,
    });
    if (!res.ok) {
      let detail = "Yükleme başarısız";
      try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
      throw new Error(detail);
    }
    return res.json();
  },
};
