from __future__ import annotations

from celery import Celery

from core.config import settings

celery_app = Celery("roundtable")
celery_app.conf.update(settings.celery_config())
celery_app.autodiscover_tasks(["worker"])
