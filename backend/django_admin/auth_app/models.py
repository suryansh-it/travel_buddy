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

    
