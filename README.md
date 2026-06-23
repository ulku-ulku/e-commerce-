# Commerce-AI — E-ticaret AI İçgörü & Karar Motoru

E-ticaret verilerini (Shopify, Meta Ads, GA4, CSV) okuyup KPI analizi yapan, AI içgörü üreten,
satış tahmini çıkaran ve aksiyon öneren full-stack SaaS.

## Stack
- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind
- **Backend:** FastAPI + SQLAlchemy 2.0 + Pydantic v2
- **DB:** PostgreSQL  •  **Queue/Cache:** Redis (RQ)
- **AI:** LLM (OpenAI-uyumlu, sağlayıcı-bağımsız) + light RAG (KPI context)  •  **Deploy:** Docker Compose

## Hızlı Başlangıç
```bash
cp .env.example .env          # LLM_API_KEY gir (opsiyonel — boşsa fallback)
docker compose up --build
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

İlk kullanıcı + örnek veri için:
```bash
docker compose exec api python -m app.seed
# login: demo@commerce.ai / demo1234
```

## Monorepo
```
commerce-ai/
├── apps/
│   ├── api/     # FastAPI backend
│   └── web/     # Next.js frontend
├── docker-compose.yml
└── .env.example
```
