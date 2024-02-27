from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured
from django.apps import apps
from django.http import Http404
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from pathlib import Path
from django.contrib.auth import logout
from celery.result import AsyncResult
import os
import shutil
from .forms import UserRegisterForm, AddProjectForm
from .models import Project, ObjectDetail, CeleryTask
from .tasks import process_project

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    success_url = reverse_lazy('password_change_done')

def scan_models_directory():
    relative_path = "models/"
    # Используем finders для поиска пути директории
    result = finders.find(relative_path, all=True)

    file_names = []

    if result:
        # Обрабатываем каждый найденный путь
        for path in result:
            # Создаем объект Path для работы с файловой системой
            path_obj = Path(path)
            if path_obj.is_dir():
                # Используем .glob("*.pt") для поиска всех файлов .pt в директории
                for model_file in path_obj.glob("*.pt"):
                    # Извлекаем имя файла и добавляем его в список
                    file_names.append(model_file.name)
            else:
                # Если result не является директорией, значит, был найден конкретный файл,
                # в этом случае добавляем его имя напрямую
                file_names.append(path_obj.name)
    else:
        print("Файлы не найдены.")

    return file_names


def get_model_path(model_type):
    # Получаем путь к директории текущего приложения
    app_dir = apps.get_app_config("agrosystems").path
    # Формируем путь к файлу модели внутри директории приложения
    model_path = os.path.join(app_dir, "static/", model_type)
    if os.path.isfile(model_path):
        return model_path
    else:
        raise ImproperlyConfigured(f"The model {model_type} does not exist")


def save_objects_to_db(project_id, objects_data):
    try:
        for data in objects_data[
            :-2
        ]:  # Исключаем последние два элемента ('output.tif' и 'Complete')
            for class_name, details in data.items():
                for obj in details["objects"]:
                    ObjectDetail.objects.create(
                        project_id=project_id,
                        class_name=class_name,
                        track_id=obj[1],
                        box_x1=obj[2][0],
                        box_y1=obj[2][1],
                        box_x2=obj[2][2],
                        box_y2=obj[2][3],
                        gps_lat=obj[3][0],
                        gps_lon=obj[3][1],
                        image_path=obj[4],
                    )
    except Exception as e:
        print(f"Ошибка при сохранении в базу данных: {e}")


def check_task_status(request, task_id):
    task_result = AsyncResult(task_id)
    if task_result.ready():
        if task_result.successful():
            # Получаем результат выполнения задачи
            result = task_result.result

            # Получаем экземпляр CeleryTask и связанный с ним проект
            task = CeleryTask.objects.get(task_id=task_id)
            project = Project.objects.get(id=task.project_id)
            # Обновляем статус проекта на 'Complete'
            project.status = "Complete"
            project.save()
            objects_data = result
            save_objects_to_db(project.id, objects_data)

            return JsonResponse({"status": "Complete"})
        else:
            # В случае ошибки обновляем статус проекта на 'Error'
            task = CeleryTask.objects.get(task_id=task_id)
            project = Project.objects.get(id=task.project_id)
            project.status = "Error"
            project.save()

            return JsonResponse({"status": "Error"})
    else:
        return JsonResponse({"status": "PROGRESS"})


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            messages.success(
                request, f"Account created for {username}! You can now log in."
            )
            return redirect("login")
    else:
        form = UserRegisterForm()
    return render(request, "agrosystems/register.html", {"form": form})


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password")
    return render(request, "agrosystems/login.html")


@login_required(login_url="/login/")
def read_root(request):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        projects = Project.objects.filter(user_id=request.user.id).values()
        # Получаем все задачи пользователя
        tasks = CeleryTask.objects.filter(user=request.user)
        for task in tasks:
            # Получаем проект, связанный с этой задачей
            project = task.project
            if project.status == "Not complete":
                # Вызываем метод check_task_status для этой задачи
                check_task_status(request, task.task_id)
        return JsonResponse({"projects": list(projects)})

    models = scan_models_directory()
    return render(request, "agrosystems/index.html", {"models": models})


@login_required
def add_project(request):
    if request.method == "POST":
        form = AddProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project_name = form.cleaned_data["project_name"]
            model_type = form.cleaned_data["model_type"]
            images = request.FILES.getlist("images")  # Получаем список файлов
            hfov = form.cleaned_data["hfov"]
            user = request.user
            # Создаем директорию для файлов проекта, если она еще не существует
            project_directory = os.path.join(
                settings.MEDIA_ROOT, f"projects/{user.id}/{project_name}"
            )
            os.makedirs(project_directory, exist_ok=True)

            # Определяем путь к модели
            model_directory = os.path.join(settings.MEDIA_ROOT, "models")
            model_path = os.path.join(model_directory, model_type)
            # Определяем путь к выходному файлу
            output_file = os.path.join(project_directory, "output.tif")

            file_paths = []
            for image in images:
                fs = FileSystemStorage(location=project_directory)
                filename = fs.save(image.name, image)
                file_path = fs.path(filename)
                file_paths.append(file_path)

            file_paths = sorted(file_paths)
            # Запуск задачи Celery
            task = process_project.delay(
                file_paths, get_model_path(model_path), output_file, hfov
            )
            project = Project.objects.create(
                project_name=project_name,
                model_type=model_type,
                status="Not complete",
                output_path=output_file,
                hfov=hfov,
                user=request.user,  # Использование текущего пользователя
            )

            CeleryTask.objects.create(
                task_id=task.id, user=request.user, project=project
            )
            # Перенаправление пользователя на страницу с индикатором выполнения задачи
            return HttpResponseRedirect("/")

    else:
        form = AddProjectForm()


@login_required
def delete_project(request, project_id):
    # Находим и удаляем все связанные ObjectDetail
    ObjectDetail.objects.filter(project_id=project_id).delete()

    # Находим проект
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise Http404("Project does not exist")

    # Удаляем проект из базы данных
    project.delete()

    # Путь к директории проекта
    project_dir = os.path.join(
        settings.MEDIA_ROOT, f"projects/{request.user.id}/{project.project_name}"
    )

    # Удаляем директорию проекта, если она существует
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)

    return JsonResponse(
        {
            "message": "Project and related object details deleted successfully, and project directory removed"
        }
    )


@login_required
def view_map(request, project_id):
    project = Project.objects.get(pk=project_id)

    object_details = ObjectDetail.objects.filter(project_id=project_id)
    object_details_data = [
        {
            "id": obj.id,
            "class_name": obj.class_name,
            "track_id": obj.track_id,
            "box_x1": obj.box_x1,
            "box_y1": obj.box_y1,
            "box_x2": obj.box_x2,
            "box_y2": obj.box_y2,
            "gps_lat": obj.gps_lat,
            "gps_lon": obj.gps_lon,
            "image_path": obj.image_path,
        }
        for obj in object_details
    ]

    context = {
        "settings": settings,
        "project": project,
        "object_details": object_details_data,
    }

    return render(request, "agrosystems/map.html", context)

@login_required
def user_profile(request):
    # Assuming you want to display information of the logged-in user
    user = request.user
    context = {
        'user': user
    }
    return render(request, 'agrosystems/user_profile.html', context)

# View for logging out
def logout_view(request):
    logout(request)
    # Redirect to homepage or login page
    return redirect('login')

@login_required
def delete_account_view(request):
    user = request.user
    user.delete()
    # Redirect to homepage or login page after account deletion
    return redirect('register')