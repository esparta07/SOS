# Generated by Django 4.2.7 on 2023-12-14 05:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0013_remove_bill_date"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="bill",
            name="days",
        ),
    ]
