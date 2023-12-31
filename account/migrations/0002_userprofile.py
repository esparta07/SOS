# Generated by Django 4.2.7 on 2023-11-29 08:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(default='', max_length=100)),
                ('u_type', models.CharField(blank=True, choices=[('FINANCE HEAD', 'FINANCE HEAD'), ('CS HEAD', 'CS HEAD'), ('RECOVERY HEAD', 'RECOVER HEAD'), ('RECOVERY AGENT', 'RECOVERY AGENT'), ('FINANCE HEAD', 'FINANCE HEAD')], max_length=40)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
