# Generated by Django 4.2.7 on 2023-12-15 09:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0017_alter_client_balance"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="overdue120",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
