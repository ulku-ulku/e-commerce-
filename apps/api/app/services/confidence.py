"""Güven/anlamlılık motoru (#5).

Her öneri, dayandığı veri hacmine göre bir güven taşır. Az veriyle verilen karar
tehlikelidir ("3 günlük veriyle kampanya kapatma"). Düşük güvenli aksiyonlar
onay gerektirir ve kuyrukta işaretlenir.
"""


def confidence(sample: float, full_at: float) -> dict:
    """sample: eldeki veri noktası sayısı; full_at: 'yeterli' sayılan eşik."""
    sample = max(0.0, float(sample))
    score = sample / (sample + full_at) if (sample + full_at) else 0.0  # 0..1, doygunlaşan
    level = "high" if score >= 0.6 else "med" if score >= 0.35 else "low"
    return {"score": round(score * 100), "level": level, "data_points": int(sample)}


LABEL = {"high": "yüksek güven", "med": "orta güven", "low": "düşük güven — veri az"}
