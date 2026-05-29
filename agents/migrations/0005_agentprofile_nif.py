from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0004_agent_coverage_zones'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentprofile',
            name='nif',
            field=models.CharField(
                blank=True,
                default='',
                help_text="Numéro d'identification fiscale (optionnel).",
                max_length=64,
            ),
        ),
    ]
