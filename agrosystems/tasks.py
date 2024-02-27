from celery import shared_task
from .utils.create_map import start_processing  # Импортируем вашу функцию обработки

@shared_task
def process_project(images_path, model_path, output_file, hfov):
    obj_counter, _, status = start_processing(images_path, model_path, output_file, hfov)
    return obj_counter, output_file, status
