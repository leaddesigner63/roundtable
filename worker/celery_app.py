from __future__ import annotations

import os

from celery import Celery

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BACKEND_URL = CELERY_BROKER_URL

app = Celery("roundtable", broker=CELERY_BROKER_URL, backend=CELERY_BACKEND_URL)
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
