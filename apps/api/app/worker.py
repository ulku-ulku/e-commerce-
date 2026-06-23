"""RQ worker — uzun süren işleri (toplu sync, batch içgörü) arka planda çalıştırır.
MVP'de insight üretimi senkron; bu worker ölçeklenme için hazır iskelettir."""
from redis import Redis
from rq import Queue, Worker

from app.core.config import settings

listen = ["default"]

if __name__ == "__main__":
    conn = Redis.from_url(settings.REDIS_URL)
    worker = Worker([Queue(name, connection=conn) for name in listen], connection=conn)
    worker.work(with_scheduler=True)
