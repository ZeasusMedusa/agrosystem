# Generated by Django 5.0.1 on 2024-02-22 08:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agrosystems", "0002_project_hfov_celerytask"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="celerytask",
            name="project_id",
        ),
        migrations.AddField(
            model_name="celerytask",
            name="project",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                to="agrosystems.project",
            ),
        ),
    ]
