from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_donationtransaction_paygatedonationstatus'),
    ]

    operations = [
        migrations.AlterField(
            model_name='donationtransaction',
            name='identifier',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
