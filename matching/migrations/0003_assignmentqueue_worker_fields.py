from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("matching", "0002_remove_assignmentrequest_celery_task_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignmentqueue",
            name="failure_notified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assignmentqueue",
            name="last_processed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assignmentqueue",
            name="next_retry_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
