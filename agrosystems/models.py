from django.db import models
from django.conf import settings

# class User(models.Model):
#     username = models.CharField(max_length=100, unique=True)
#     hashed_password = models.CharField(max_length=100)
#     is_active = models.BooleanField(default=True)

class Project(models.Model):
    project_name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=100)
    status = models.CharField(max_length=100, default="Not complete")
    output_path = models.CharField(max_length=100)
    hfov = models.FloatField(default=67)
    # user = models.ForeignKey(User, related_name='projects', on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', related_name='projects', on_delete=models.CASCADE)


class ObjectDetail(models.Model):
    class_name = models.CharField(max_length=100)
    track_id = models.IntegerField()
    box_x1 = models.FloatField()
    box_y1 = models.FloatField()
    box_x2 = models.FloatField()
    box_y2 = models.FloatField()
    gps_lat = models.FloatField()
    gps_lon = models.FloatField()
    image_path = models.CharField(max_length=100)
    project = models.ForeignKey(Project, related_name='object_details', on_delete=models.CASCADE)


class CeleryTask(models.Model):
    task_id = models.CharField(max_length=50, unique=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, default=None)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"CeleryTask {self.task_id}"