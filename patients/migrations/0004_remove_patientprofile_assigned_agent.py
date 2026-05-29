from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0003_patientprofile_assigned_agent'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='patientprofile',
            name='assigned_agent',
        ),
    ]
