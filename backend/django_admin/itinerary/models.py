from django.db import models
from country.models import AppCategory, TravelApp

class Itinerary(models.Model):
    """
    A user’s trip, composed of ordered stops.
    """
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Stop(models.Model):
    """
    A single stop in an itinerary (a “leg”).
    We assign it a type (e.g., beach, mountain, city) so we can recommend apps.
    """
    TYPE_CHOICES = [
        ('beach', 'Beach'),
        ('mountain', 'Mountain'),
        ('city', 'City'),
        ('desert', 'Desert'),
        ('ski', 'Ski Resort'),
        # …
    ]

    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name="stops")
    name = models.CharField(max_length=200)  
    stop_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.itinerary.name} → {self.name}"

class LegSuggestionRule(models.Model):
    """
    Simple mapping: for each stop_type, suggest these categories.
    """
    stop_type = models.CharField(max_length=20, choices=Stop.TYPE_CHOICES, unique=True)
    categories = models.ManyToManyField(AppCategory, help_text="Which app categories to suggest")

    def __str__(self):
        return f"{self.stop_type} → {','.join(c.name for c in self.categories.all())}"
