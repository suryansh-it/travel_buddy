from django.conf import settings
from django.db import models

from country.models import Country


class UserOriginPreference(models.Model):
	"""Stores a logged-in user's selected origin country for travel personalization."""

	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="origin_preference",
	)
	origin_country = models.ForeignKey(
		Country,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="user_origin_preferences",
	)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		country_code = self.origin_country.code if self.origin_country else "None"
		return f"{self.user_id} -> {country_code}"


class UserCountrySuggestion(models.Model):
	"""Stores a logged-in user's country suggestion submission."""

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="country_suggestions",
	)
	country = models.CharField(max_length=255)
	message = models.TextField()
	user_email = models.EmailField(blank=True)
	user_name = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.user_id} -> {self.country}"


class UserFeedback(models.Model):
	"""Stores a logged-in user's feedback submission."""

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="feedback_entries",
	)
	name = models.CharField(max_length=255, blank=True)
	message = models.TextField()
	user_email = models.EmailField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.user_id} -> feedback"


class Bookmark(models.Model):
	"""Stores user bookmarks for countries and travel apps."""
	
	BOOKMARK_TYPES = [
		('country', 'Country'),
		('app', 'Travel App'),
	]
	
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="bookmarks",
	)
	bookmark_type = models.CharField(max_length=10, choices=BOOKMARK_TYPES)
	country = models.ForeignKey(
		'country.Country',
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name="bookmarks",
	)
	app = models.ForeignKey(
		'country.TravelApp',
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name="bookmarks",
	)
	created_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		unique_together = [
			('user', 'country', 'bookmark_type'),
			('user', 'app', 'bookmark_type'),
		]
	
	def __str__(self):
		if self.bookmark_type == 'country' and self.country:
			return f"{self.user.username} bookmarked {self.country.name}"
		elif self.bookmark_type == 'app' and self.app:
			return f"{self.user.username} bookmarked {self.app.name}"
		return f"{self.user.username} bookmark"

    
