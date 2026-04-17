from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("country", "0007_alter_travelapp_android_link_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OriginCountryAssistance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=255)),
                ("emergency_phone", models.CharField(blank=True, default="", max_length=80)),
                ("emergency_phone_intl", models.CharField(blank=True, default="", max_length=80)),
                ("consular_address", models.CharField(blank=True, default="", max_length=400)),
                ("website", models.URLField(blank=True, default="", max_length=500)),
                ("mission_finder", models.URLField(blank=True, default="", max_length=500)),
                ("source", models.CharField(blank=True, default="", max_length=80)),
                ("fetched_at", models.DateTimeField(auto_now=True)),
                (
                    "country",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="origin_assistance_profile", to="country.country"),
                ),
            ],
        ),
    ]
