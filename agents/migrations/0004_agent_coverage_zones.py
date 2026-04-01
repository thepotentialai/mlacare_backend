from django.db import migrations, models


def forwards_residence_to_coverage(apps, schema_editor):
    AgentProfile = apps.get_model('agents', 'AgentProfile')
    for ap in AgentProfile.objects.filter(residence_zone_id__isnull=False).iterator():
        ap.coverage_zones.add(ap.residence_zone_id)


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('agents', '0003_profession_replace_professional_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentprofile',
            name='coverage_zones',
            field=models.ManyToManyField(
                blank=True,
                help_text="Zones de résidence que l'agent accepte de couvrir (assignation patient).",
                related_name='covering_agents',
                to='agents.residencezone',
            ),
        ),
        migrations.RunPython(forwards_residence_to_coverage, backwards_noop),
    ]
