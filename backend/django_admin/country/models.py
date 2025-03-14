from django.db import models

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)  # e.g., "CN" for China, "US" for USA
    flag = models.ImageField(upload_to="flags/", blank=True, null=True)  # Optional flag image
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class AppCategory(models.Model):
    """
    Categories for travel apps (e.g., Navigation, Communication, Finance).
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class TravelApp(models.Model):
    """
    Travel apps available in a specific country.
    """
    name = models.CharField(max_length=255, unique=True)
    icon_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(AppCategory, on_delete=models.CASCADE, related_name="apps")
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="apps")
    android_link = models.URLField(blank=True, null=True)
    ios_link = models.URLField(blank=True, null=True)
    website_link = models.URLField(blank=True, null=True)
    supports_foreign_cards = models.BooleanField(default=False)
    works_offline = models.BooleanField(default=False)

    def __str__(self):
        return self.name

