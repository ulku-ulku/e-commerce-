"""Evrensel/akıllı içe-aktarıcı — HER e-ticaret dosyasını kabul eder (CSV + Excel).

Sabit "tarih,ciro" şartı yerine kolonları esnek tanır (TR+EN + alt-dize eşleşmesi),
satır-seviyesi (sipariş/işlem) veriyi otomatik GÜNLÜK ciroya toplar.
Shopify/Woo/pazaryeri raporları, Olist order_items, Excel ihracatları vb. çalışır.
"""
import csv
import io
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import SalesRecord

# Rol -> olası kolon adları (tam veya alt-dize eşleşir). Sıra = öncelik.
ROLES = {
    "date": ["order_purchase_timestamp", "order_date", "created_at", "purchase", "invoicedate",
             "transaction_date", "shipping_limit_date", "tarih", "date", "day", "datetime",
             "timestamp", "gün", "gun", "islem_tarihi"],
    "total": ["net_sales", "total_price", "grand_total", "line_total", "revenue", "ciro", "gelir",
              "gmv", "sales", "amount", "payment_value", "tutar", "toplam", "total"],
    "price": ["unit_price", "birim_fiyat", "price", "fiyat"],
    "qty": ["quantity", "order_item_qty", "qty", "adet", "miktar", "units"],
    "order": ["order_id", "order_number", "invoice_no", "invoiceno", "invoice", "siparis",
              "transaction_id", "order"],
    "channel": ["sales_channel", "payment_type", "marketplace", "channel", "kanal", "kaynak",
                "platform", "store", "magaza", "source"],
}

DATE_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y %H:%M",
                "%d/%m/%Y %H:%M", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y"]


def _detect(headers: list[str]) -> dict:
    norm = [(h, (h or "").lower().strip()) for h in headers]
    found = {}
    for role, names in ROLES.items():
        for cand in names:
            hit = next((orig for orig, low in norm if low == cand), None) \
                or next((orig for orig, low in norm if cand in low), None)
            if hit:
                found[role] = hit
                break
    return found


def _num(v):
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ".").strip()) if v not in (None, "") else 0.0
    except ValueError:
        return 0.0


def _parse_date(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    if not s:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s[:len(fmt) + 2] if len(s) > 10 else s, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _rows_from_csv(raw: bytes):
    text = raw.decode("utf-8-sig", errors="replace")
    sample = text[:4000]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    return (reader.fieldnames or []), list(reader)


def _rows_from_xlsx(raw: bytes):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    try:
        first = next(it)
    except StopIteration:
        return [], []
    headers = [str(h).strip() if h is not None else "" for h in first]
    rows = []
    for r in it:
        if r is None or all(c is None for c in r):
            continue
        rows.append(dict(zip(headers, r)))
    return headers, rows


def _ingest_rows(db: Session, org_id: int, headers: list[str], rows: list[dict]) -> dict:
    cols = _detect(headers)
    if "date" not in cols:
        raise ValueError(
            f"Tarih kolonu bulunamadı. Bu dosya zaman serisine eklenemez (ör. ödeme/ürün tablosu). "
            f"Başlıklar: {headers}")
    value_col = cols.get("total") or cols.get("price")
    if not value_col:
        raise ValueError(f"Ciro/fiyat kolonu bulunamadı. Başlıklar: {headers}")

    value_is_unit = value_col == cols.get("price") and "total" not in cols
    daily = defaultdict(lambda: {"rev": 0.0, "orders": set(), "rows": 0})
    used = 0
    for row in rows:
        day = _parse_date(row.get(cols["date"]))
        if not day:
            continue
        qty = (int(_num(row.get(cols["qty"]))) or 1) if "qty" in cols else 1
        val = _num(row.get(value_col))
        rev = val * qty if value_is_unit else val
        ch = (str(row.get(cols["channel"], "")).strip() or "upload") if "channel" in cols else "upload"
        d = daily[(day, ch[:40])]
        d["rev"] += rev
        d["rows"] += 1
        if "order" in cols:
            d["orders"].add(row.get(cols["order"]))
        used += 1

    if not daily:
        raise ValueError("Geçerli satır bulunamadı (tarih/değer okunamadı).")

    db.execute(delete(SalesRecord).where(SalesRecord.org_id == org_id, SalesRecord.source == "upload"))
    for (day, ch), d in daily.items():
        db.add(SalesRecord(org_id=org_id, source="upload", day=day, channel=ch,
                           revenue=round(d["rev"], 2),
                           orders=len(d["orders"]) if d["orders"] else d["rows"],
                           sessions=0, ad_spend=0.0))
    db.commit()

    days = sorted({k[0] for k in daily})
    return {
        "rows_ingested": used,
        "source": "upload",
        "detected": {k: cols[k] for k in cols},
        "summary": (f"{used} satır işlendi → {len(daily)} gün-kanal. "
                    f"Tarih: {min(days)}..{max(days)}. "
                    f"Algılanan: tarih='{cols['date']}', ciro='{value_col}'"
                    + (f", kanal='{cols['channel']}'" if 'channel' in cols else "")
                    + (f", sipariş='{cols['order']}'" if 'order' in cols else "")),
    }


def smart_ingest(db: Session, org_id: int, raw: bytes, filename: str = "") -> dict:
    fn = (filename or "").lower()
    is_xlsx = fn.endswith((".xlsx", ".xlsm")) or raw[:2] == b"PK"  # PK = zip = xlsx imzası
    if fn.endswith(".xls") and raw[:2] != b"PK":
        raise ValueError("Eski .xls formatı desteklenmiyor — lütfen .xlsx veya .csv olarak kaydet.")
    headers, rows = _rows_from_xlsx(raw) if is_xlsx else _rows_from_csv(raw)
    return _ingest_rows(db, org_id, headers, rows)
