from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("matching", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="assignmentrequest",
            name="celery_task_id",
        ),
    ]
