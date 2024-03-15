from __future__ import absolute_import, unicode_literals
import os
from celery.schedules import crontab
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SOS.settings')

app = Celery('SOS')
app.conf.enable_utc = False

app.conf.update(timezone = 'Asia/Kathmandu')

app.config_from_object(settings, namespace='CELERY')

# Celery Beat Settings
app.conf.beat_schedule = {
    # 'run-generate-and-send-excel-task': {
    #     'task': 'project.tasks.generate_and_send_html_tables',
    #     'schedule': crontab(hour=13, minute=10),  # Run daily at 9:30am
    # },
    # 'run-generate-and-send-compiled-excel-task': {
    #     'task': 'project.tasks.generate_and_send_compiled_excel',
    #     'schedule': crontab(hour=13, minute=10),  # Run daily at 9:250am 
    # },
}


app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')