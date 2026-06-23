"""Kural-tabanlı karar motoru — KPI'lardan deterministik sinyaller üretir.
AI katmanı bu sinyalleri 'context/RAG' olarak kullanıp doğal dilde açıklar."""


def evaluate(kpi: dict, forecast: list[dict]) -> list[dict]:
    signals: list[dict] = []

    if kpi["roas"] and kpi["roas"] < 2.0 and kpi["ad_spend"] > 0:
        signals.append({
            "code": "low_roas",
            "severity": "critical",
            "message": f"ROAS {kpi['roas']} — reklam harcaması verimsiz (eşik 2.0).",
            "action": "Düşük performanslı kampanyaları durdur, en yüksek ROAS'lı setlere bütçe kaydır.",
        })

    if kpi["conversion_rate"] and kpi["conversion_rate"] < 1.5:
        signals.append({
            "code": "low_conversion",
            "severity": "warning",
            "message": f"Dönüşüm oranı %{kpi['conversion_rate']} — sektör ortalamasının altında.",
            "action": "Checkout akışını ve ürün sayfası hızını incele; sepet terk e-postası kur.",
        })

    if kpi["revenue_delta_pct"] < -10:
        signals.append({
            "code": "revenue_drop",
            "severity": "critical",
            "message": f"Ciro önceki döneme göre %{kpi['revenue_delta_pct']} düştü.",
            "action": "Kanal bazında düşüşü ayrıştır; stok ve fiyat değişikliklerini kontrol et.",
        })

    if forecast:
        avg_fc = sum(p["predicted_revenue"] for p in forecast) / len(forecast)
        recent = kpi["revenue"] / 30 if kpi["revenue"] else 0
        if recent and avg_fc > recent * 1.1:
            signals.append({
                "code": "growth_opportunity",
                "severity": "info",
                "message": "Tahmin yükseliş trendi gösteriyor.",
                "action": "Stok seviyelerini artır, en çok satan SKU'larda reklam bütçesini ölçekle.",
            })

    return signals
