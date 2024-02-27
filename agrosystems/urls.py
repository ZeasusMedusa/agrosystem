from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('', views.read_root, name='home'),
    path('add-project/', views.add_project, name='add_project'),
    path('check-task-status/<task_id>', views.check_task_status, name='check_task_status'),
    path('view-map/<int:project_id>/', views.view_map, name='view_map'),
    path('delete-project/<int:project_id>/', views.delete_project, name='delete-project'),
    path('user/', views.user_profile, name='user_profile'),
    path('logout/', views.logout_view, name='logout'),
    path('delete_account/', views.delete_account_view, name='delete_account'),
    path('password_change/', views.CustomPasswordChangeView.as_view(), name='change_password'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
