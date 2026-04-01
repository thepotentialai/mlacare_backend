from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visits', '0002_add_subscription_visit_number_completed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='visit',
            name='rescheduled_from',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Date originale avant report'),
        ),
    ]
