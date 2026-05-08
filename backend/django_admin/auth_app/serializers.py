from rest_framework import serializers

from .models import UserOriginPreference, Bookmark


class UserOriginPreferenceSerializer(serializers.ModelSerializer):
	origin_country = serializers.SerializerMethodField()

	class Meta:
		model = UserOriginPreference
		fields = ["origin_country", "updated_at"]

	def get_origin_country(self, obj):
		country = obj.origin_country
		if not country:
			return None
		return {
			"code": country.code,
			"name": country.name,
		}


class BookmarkSerializer(serializers.ModelSerializer):
	country_data = serializers.SerializerMethodField()
	app_data = serializers.SerializerMethodField()

	class Meta:
		model = Bookmark
		fields = ["id", "bookmark_type", "country", "app", "country_data", "app_data", "created_at"]

	def get_country_data(self, obj):
		if obj.country:
			return {
				"id": obj.country.id,
				"code": obj.country.code,
				"name": obj.country.name,
				"flag": obj.country.flag.url if obj.country.flag else None,
			}
		return None

	def get_app_data(self, obj):
		if obj.app:
			return {
				"id": obj.app.id,
				"name": obj.app.name,
				"icon_url": obj.app.icon_url,
				"category": obj.app.category.name if obj.app.category else None,
				"country": obj.app.country.code if obj.app.country else None,
			}
		return None

