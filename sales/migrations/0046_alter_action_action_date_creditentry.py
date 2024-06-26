# Generated by Django 4.2.7 on 2024-04-25 05:25

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sales', '0045_rename_short_name_action_account_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='action_date',
            field=models.DateTimeField(default=datetime.datetime(2024, 4, 25, 9, 30)),
        ),
        migrations.CreateModel(
            name='CreditEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('settle', models.BooleanField(default=False)),
                ('account_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sales.client')),
                ('collector', models.ForeignKey(blank=True, limit_choices_to={'role': 2}, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='credit', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
