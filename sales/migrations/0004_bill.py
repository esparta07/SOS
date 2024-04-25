# Generated by Django 4.2.7 on 2023-12-08 07:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0003_alter_client_short_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(blank=True, choices=[('OB', 'OB'), ('SB', 'SB')], max_length=40)),
                ('bill_no', models.CharField(blank=True, choices=[('OB', 'OB'), ('SB', 'SB')], max_length=40)),
                ('date', models.DateField()),
                ('due_date', models.DateField()),
                ('days', models.IntegerField()),
                ('inv_amount', models.FloatField()),
                ('cycle1', models.FloatField()),
                ('cycle2', models.FloatField()),
                ('cycle3', models.FloatField()),
                ('cycle4', models.FloatField()),
                ('cycle5', models.FloatField()),
                ('cycle6', models.FloatField()),
                ('cycle7', models.FloatField()),
                ('cycle8', models.FloatField()),
                ('cycle9', models.FloatField()),
                ('balance', models.FloatField()),
                ('short_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sales.client')),
            ],
        ),
    ]
