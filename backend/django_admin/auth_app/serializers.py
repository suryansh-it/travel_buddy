from rest_framework import serializers

from .models import UserOriginPreference


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
