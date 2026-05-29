import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0005_agentprofile_nif'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentprofile',
            name='pending_residence_zone',
            field=models.ForeignKey(
                blank=True,
                help_text="Zone de résidence demandée par l'agent (en attente validation admin).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pending_residence_agents',
                to='agents.residencezone',
            ),
        ),
        migrations.AddField(
            model_name='agentprofile',
            name='pending_coverage_zones',
            field=models.ManyToManyField(
                blank=True,
                help_text='Zones de couverture demandées (en attente validation admin).',
                related_name='pending_coverage_by_agents',
                to='agents.residencezone',
            ),
        ),
    ]
