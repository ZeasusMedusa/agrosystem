from celery import Celery
import os

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrosystem.settings')

# Define the Celery app
app = Celery('agrosystems', broker='redis://localhost:6379/0')

# Optional configuration
app.conf.update(
    result_backend='redis://localhost:6379/0',
    timezone='UTC',
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    worker_prefetch_multiplier=1
)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
