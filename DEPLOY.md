# Deploy — Render

Bu proje `render.yaml` ile Render'a tek seferde kurulur (PostgreSQL + backend + frontend).

## Adımlar

### 1. Render hesabı + Blueprint
1. https://render.com → GitHub ile giriş yap (ücretsiz)
2. **New + → Blueprint**
3. `ulku-ulku/e-commerce-` repo'sunu seç → Render `render.yaml`'ı okur
4. **Apply** → 3 servis oluşur: `commerce-ai-db`, `commerce-ai-api`, `commerce-ai-web`

İlk build birkaç dakika sürer. Backend ilk açılışta demo veriyi otomatik yükler (`SEED_ON_START=1`).

### 2. Frontend'i backend'e bağla (tek manuel adım)
Next.js, API adresini **build sırasında** gömer. O yüzden:
1. Backend deploy bitince URL'sini kopyala (ör. `https://commerce-ai-api.onrender.com`)
2. **commerce-ai-web → Environment → `NEXT_PUBLIC_API_URL`** değerine bu URL'yi yaz
3. **Manual Deploy → Deploy latest commit** (web servisini yeniden derle)

### 3. Aç
- Frontend: `https://commerce-ai-web.onrender.com`
- Giriş: `demo@commerce.ai` / `demo1234`
- API docs: `https://commerce-ai-api.onrender.com/docs`

## Notlar
- **Ücretsiz kademe:** Servisler ~15 dk işlemsizlikten sonra uykuya dalar; ilk istek yavaş açılır (cold start). Ücretsiz Postgres ~90 gün sonra silinir.
- **AI tam modu:** `commerce-ai-api → LLM_API_KEY`'e OpenAI-uyumlu bir anahtar girersen asistan/içgörü tam LLM ile çalışır (boşsa deterministik fallback).
- **Gerçek mağaza:** Dashboard'da pazaryeri bağla veya CSV/Excel yükle → kendi verinle çalışır.
- **CORS:** `ALLOWED_ORIGINS` "*" (Bearer token kullanıldığı için güvenli). İstersen sadece frontend URL'sine kısıtla.
