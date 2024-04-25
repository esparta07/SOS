# Generated by Django 4.2.7 on 2024-04-22 09:22

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0042_logentry_alter_action_action_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bill',
            name='balance',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='cycle1',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='cycle2',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='cycle3',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='cycle4',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='cycle5',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='cycle6',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='cycle7',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='cycle8',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='cycle9',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='type',
        ),
        migrations.AlterField(
            model_name='action',
            name='action_date',
            field=models.DateTimeField(default=datetime.datetime(2024, 4, 22, 9, 30)),
        ),
    ]