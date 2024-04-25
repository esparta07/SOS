# Generated by Django 4.2.7 on 2023-12-01 06:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Client",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("vat_number", models.CharField(max_length=20)),
                ("name", models.CharField(max_length=255)),
                ("address", models.TextField()),
                ("group", models.CharField(max_length=100)),
                ("guarantee_world_insurer", models.CharField(max_length=255)),
                ("credit_limit", models.DecimalField(decimal_places=2, max_digits=15)),
                (
                    "collector",
                    models.ForeignKey(
                        limit_choices_to={"role": 2},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="clients",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
