from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from cattube.core.utils import url_path_join
from cattube.settings import VIDEOS_PATH, THUMBNAILS_PATH
from pydantic import RootModel
from typing import List
from twelvelabs.models import VideoValue, SearchData

class Video(models.Model):
    title = models.CharField(max_length=256)
    uploaded_at = models.DateTimeField(default=timezone.now)
    video = models.FileField()
    thumbnail = models.FileField()
    transcription = models.FileField()
    text_in_video = models.FileField()
    logo = models.FileField()
    status = models.CharField(max_length=16, default='')
    video_id = models.CharField(max_length=32, default='')
    user = models.ForeignKey(User, related_name='videos', on_delete=models.CASCADE)

    ordering = ["-uploaded_at"]

    def __str__(self):
        return f'"{self.title}", uploaded at {self.uploaded_at}, assembly_id {self.assembly_id}, original {self.video}, user {self.user.username}'

    def update_from_assembly(self, assembly):
        self.video = url_path_join(VIDEOS_PATH, assembly['results'][':original'][0]['name'])
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

    video = models.ForeignKey("Video", on_delete=models.DO_NOTHING)
    clip_count = models.IntegerField()
    clips = models.CharField(max_length=10240)


class VideoValueList(RootModel):
    """
    Wrapper so we can easily serialize lists of VideoValue objects back to JSON
    """
    root: List[VideoValue]


class SearchDataList(RootModel):
    """
    Wrapper so we can easily serialize lists of SearchData objects back to JSON
    """
    root: List[SearchData]
