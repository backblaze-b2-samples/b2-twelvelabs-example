from django.contrib.auth.models import User
from django.db import models

from cattube.settings import VIDEOS_PATH, THUMBNAILS_PATH


class Video(models.Model):
    title = models.CharField(max_length=256)
    assembly_id = models.CharField(max_length=256)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original = models.FileField()
    thumbnail = models.FileField()
    status = models.CharField(max_length=16, default='')
    video_id = models.CharField(max_length=32, default='')
    user = models.ForeignKey(User, related_name='videos', on_delete=models.CASCADE)

    def __str__(self):
        return f'"{self.title}", uploaded at {self.uploaded_at}, assembly_id {self.assembly_id}, original {self.original}, user {self.user.username}'

    def update_with_assembly(self, assembly):
        self.original = VIDEOS_PATH + '/' + assembly['assembly_id'] + '/' + assembly['results'][VIDEOS_PATH][0]['name']
        self.thumbnail = THUMBNAILS_PATH + '/' + assembly['assembly_id'] + '/' + assembly['results'][THUMBNAILS_PATH][0]['name']
        print(f'Saving {self}')
        self.save()


class Notification(models.Model):
    transloadit = models.CharField(max_length=65536)
    signature = models.CharField(max_length=40)


class GroupField(models.Field):
    """
    Holder for the search result's group
    """
    pass


class SearchResult(models.Model):
    """
    In-memory model, so we can pass search results from the view to the template
    """
    managed = False

    video = models.OneToOneField(Video, on_delete=models.CASCADE)
    group = GroupField()
