from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db import models
from django.utils import timezone

from cattube.core.utils import url_path_join
from cattube.settings import VIDEOS_PATH


class Video(models.Model):
    title = models.CharField(max_length=256)
    assembly_id = models.CharField(max_length=256, default='')
    uploaded_at = models.DateTimeField(default=timezone.now)
    video = models.FileField(null=True)
    thumbnail = models.FileField(null=True)
    status = models.CharField(max_length=16, default='')
    video_id = models.CharField(max_length=32, default='')
    user = models.ForeignKey(User, related_name='videos', on_delete=models.CASCADE)

    ordering = ["-uploaded_at"]

    def __str__(self):
        return f'"{self.title}", uploaded at {self.uploaded_at}, assembly_id {self.assembly_id}, original {self.video}, user {self.user.username}'

    @property
    def done(self):
        return self.status in ("Ready", "Failed")

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
    clip_count = models.IntegerField(default=0)
    clips = models.CharField(max_length=10240, default='')


def add_new_files(user):
    """
    Helper function to list files in the default storage, adding them to the database if they do not already exist.
    """
    if user.is_authenticated:
        directories, files = default_storage.listdir(f'{VIDEOS_PATH}')
        videos = Video.objects.all()
        new_videos = []
        for file in files:
            path_to_file = url_path_join(VIDEOS_PATH, file)
            if len(videos.filter(video__exact=path_to_file)) == 0:
                new_videos.append(Video(
                    video=path_to_file,
                    title=Path(file).stem,
                    user=user,
                   uploaded_at=default_storage.get_modified_time(path_to_file)))
        if len(new_videos) > 0:
            Video.objects.bulk_create(new_videos)
