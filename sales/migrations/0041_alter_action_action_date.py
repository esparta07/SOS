# Generated by Django 4.2.7 on 2024-03-15 04:35

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0040_rename_completed_client_pause'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='action_date',
            field=models.DateTimeField(default=datetime.datetime(2024, 3, 15, 9, 30)),
        ),
    ]
