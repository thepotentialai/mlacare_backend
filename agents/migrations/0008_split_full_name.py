from django.db import migrations, models


def migrate_full_name_to_last_name(apps, schema_editor):
    AgentProfile = apps.get_model('agents', 'AgentProfile')
    for profile in AgentProfile.objects.all():
        profile.last_name = profile.full_name or ''
        profile.first_name = ''
        profile.save(update_fields=['last_name', 'first_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0007_alter_agentprofile_coverage_zones'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentprofile',
            name='first_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='agentprofile',
            name='last_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.RunPython(migrate_full_name_to_last_name, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='agentprofile',
            name='full_name',
        ),
        migrations.AlterField(
            model_name='agentprofile',
            name='last_name',
            field=models.CharField(max_length=100),
        ),
    ]
