# Generated by Django 5.0.1 on 2024-02-22 10:10

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agrosystems", "0005_celerytask_status"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="celerytask",
            name="status",
        ),
        migrations.AlterField(
            model_name="project",
            name="status",
            field=models.CharField(default="Not complete", max_length=100),
        ),
    ]
