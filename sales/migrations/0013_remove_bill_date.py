# Generated by Django 4.2.7 on 2023-12-14 04:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0012_alter_bill_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bill',
            name='date',
        ),
    ]
