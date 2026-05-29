from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('matching', '0003_assignmentqueue_worker_fields'),
        # patients migration that removes assigned_agent must run first
        ('patients', '0004_remove_patientprofile_assigned_agent'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AssignmentRequest',
        ),
        migrations.DeleteModel(
            name='AssignmentQueue',
        ),
    ]
