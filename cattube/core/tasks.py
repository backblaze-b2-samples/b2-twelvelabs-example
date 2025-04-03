import json
from io import BytesIO
from pathlib import Path
from time import sleep
from urllib.parse import urlparse
from urllib.request import urlopen

from django.core.files.storage import default_storage
from huey.contrib import djhuey as huey
from transloadit import client as transload_it
from twelvelabs import BadRequestError

from cattube.core.models import Video
from cattube.core.utils import url_path_join
from cattube.settings import TRANSLOADIT_KEY, TRANSLOADIT_SECRET, TWELVE_LABS_CLIENT, TWELVE_LABS_POLL_INTERVAL, \
    TWELVE_LABS_INDEX_ID, THUMBNAILS_PATH


@huey.db_task()
def do_video_indexing(video_tasks):
    print(f'Creating tasks: {video_tasks}')

    # Create a task for each video we want to index
    error_tasks = []
    for video_task in video_tasks:
        try:
            task = TWELVE_LABS_CLIENT.task.create(
                TWELVE_LABS_INDEX_ID,
                url=default_storage.url(video_task['video']),
                enable_video_stream=False
            )
            print(f'Created task: {task}')
            video_task['task_id'] = task.id
        except BadRequestError as ex:
            print(f'Error indexing {video_task['video']}: {ex.message}')
            error_tasks.append(video_task)

    print(f'{len(error_tasks)} errors creating tasks')
    if len(error_tasks) > 0:
        video_ids = [error_task['id'] for error_task in error_tasks]
        videos = Video.objects.filter(id__in=video_ids)
        for video in videos:
            video.status = 'Error'
        Video.objects.bulk_update(videos, ['status'])
        video_tasks = [video_task for video_task in video_tasks if video_task not in error_tasks]

    print(f'Created {len(video_tasks)} tasks')

    print(f'Polling Twelve Labs for {video_tasks}')

    # Do a single database query for all the videos we're interested in
    video_ids = [video_task['id'] for video_task in video_tasks]
    videos = Video.objects.filter(id__in=video_ids)

    while True:
        done = True
        videos_to_save = []

        # Retrieve status for each task we created
        for video_task in video_tasks:
            # What's our current state for this video?
            video = videos.get(video__exact=video_task['video'])

            # Do we still need to retrieve status for this task?
            if not video.done:
                task = TWELVE_LABS_CLIENT.task.retrieve(video_task['task_id'])
                if not task.done:
                    # We'll need to go round the loop again
                    done = False

                # Do we need to write a new status to the DB?
                if video.status.lower() != task.status:
                    # We store the status in the DB in title case, so it's ready to render on the page
                    new_status = task.status.title()
                    print(f'Updating status for {video_task["video"]} from {video.status} to {new_status}')
                    video.status = new_status
                    if task.done:
                        video.video_id = task.video_id
                        get_thumbnail(video)
                    videos_to_save.append(video)

        if len(videos_to_save) > 0:
            Video.objects.bulk_update(videos_to_save, ['status', 'video_id', THUMBNAILS_PATH])

        if done:
            break

        sleep(TWELVE_LABS_POLL_INTERVAL)

    print(f'Done polling {video_tasks}')


def get_thumbnail(video: Video):
    print(f'Getting thumbnail for {video.video_id}')
    # Need to get the task to get the hls with the thumbnail ID
    task = TWELVE_LABS_CLIENT.task.retrieve(video.video_id)
    print(f'Got response: {task}')

    if task.hls and task.hls.thumbnail_urls and len(task.hls.thumbnail_urls) > 0:
        thumbnail_url = task.hls.thumbnail_urls[0]

        url_parts = urlparse(thumbnail_url)
        thumbnail_path = url_path_join(THUMBNAILS_PATH, f'{video.video_id}{Path(url_parts.path).suffix}')

        print(f'Saving {thumbnail_url} to {thumbnail_path}')
        default_storage.save(thumbnail_path, urlopen(thumbnail_url))
        video.thumbnail = thumbnail_path
    else:
        print(f'No thumbnail for {video.video_id}')


def assembly_finished(assembly):
    """
    Helper based on https://github.com/transloadit/python-sdk/blob/faf225badafe59c311622ab63610f432aac8a77b/transloadit/assembly.py#L127
    """
    status = assembly.get("ok")
    is_aborted = status == "REQUEST_ABORTED"
    is_canceled = status == "ASSEMBLY_CANCELED"
    is_completed = status == "ASSEMBLY_COMPLETED"
    error = assembly.get("error")
    is_failed = error is not None
    is_fetch_rate_limit = error == "ASSEMBLY_STATUS_FETCHING_RATE_LIMIT_REACHED"
    return is_aborted or is_canceled or is_completed or (is_failed and not is_fetch_rate_limit)


@huey.db_task()
def poll_video_loading(assembly_id):
    print(f'Polling TransloadIt for {assembly_id}')

    client = transload_it.Transloadit(TRANSLOADIT_KEY, TRANSLOADIT_SECRET)

    while True:
        response = client.get_assembly(assembly_id)
        assembly = response.data
        print(f"Found assembly: {json.dumps(assembly, indent=2)}")
        if assembly_finished(assembly):
            video = Video.objects.get(assembly_id__exact=assembly_id)
            video.update_from_assembly(assembly)
            break

        sleep(1)

    print(f'Done polling {assembly_id}')
