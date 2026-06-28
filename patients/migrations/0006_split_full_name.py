from django.db import migrations, models


def migrate_full_name_to_last_name(apps, schema_editor):
    PatientProfile = apps.get_model('patients', 'PatientProfile')
    for profile in PatientProfile.objects.all():
        profile.last_name = profile.full_name or ''
        profile.first_name = ''
        profile.save(update_fields=['last_name', 'first_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0005_add_structured_health_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='patientprofile',
            name='first_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='patientprofile',
            name='last_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.RunPython(migrate_full_name_to_last_name, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='patientprofile',
            name='full_name',
        ),
        migrations.AlterField(
            model_name='patientprofile',
            name='last_name',
            field=models.CharField(max_length=100),
        ),
    ]
