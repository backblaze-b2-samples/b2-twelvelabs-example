from rest_framework import serializers

from .models import Notification, Video


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ['title', 'uploaded_at', 'original', 'thumbnail', 'user']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['transloadit', 'signature']
