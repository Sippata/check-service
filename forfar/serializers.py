from rest_framework import serializers

from .models import Check


class CheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Check
        fields = ['id']
