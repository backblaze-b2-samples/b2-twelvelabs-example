import json
from io import BytesIO
from pathlib import Path

from django.core.files.storage import default_storage
from huey.contrib import djhuey as huey
from time import sleep
from transloadit import client as TransloadIt
from urllib.parse import urlparse, urlunsplit
from urllib.request import urlopen

from cattube.core.models import Video, VideoValueList
from cattube.core.utils import url_path_join
from cattube.settings import TRANSLOADIT_KEY, TRANSLOADIT_SECRET, TWELVE_LABS_CLIENT, TWELVE_LABS_POLL_INTERVAL, \
    TWELVE_LABS_INDEX_ID, THUMBNAILS_PATH, TRANSCRIPTS_PATH, TEXT_PATH, LOGOS_PATH


@huey.db_task()
def do_video_indexing(video_tasks):
    print(f'Creating tasks: {video_tasks}')

    # Create a task for each video we want to index
    for video_task in video_tasks:
        task = TWELVE_LABS_CLIENT.task.create(
            TWELVE_LABS_INDEX_ID,
            url=default_storage.url(video_task['video']),
            disable_video_stream=True
        )
        print(f'Created task: {task}')
        video_task['task_id'] = task.id

    print(f'Created {len(video_tasks)} tasks')

    print(f'Polling Twelve Labs for {video_tasks}')

    # Do a single database query for all the videos we're interested in
    video_names = [video_task['video'] for video_task in video_tasks]
    videos = Video.objects.filter(video__in=video_names)

    while True:
        done = True
        videos_to_save = []

        # Retrieve status for each task we created
        for video_task in video_tasks:
            # What's our current state for this video?
            video = videos.get(video__exact=video_task['video'])

            # Do we still need to retrieve status for this task?
            if video.status != 'Ready':
                task = TWELVE_LABS_CLIENT.task.retrieve(video_task['task_id'])
                if task.status != 'ready':
                    # We'll need to go round the loop again
                    done = False

                # Do we need to write a new status to the DB?
                if video.status.lower() != task.status:
                    # We store the status in the DB in title case, so it's ready to render on the page
                    new_status = task.status.title()
                    print(f'Updating status for {video_task["video"]} from {video.status} to {new_status}')
                    video.status = new_status
                    if task.status == 'ready':
                        video.video_id = task.video_id
                        get_all_video_data(video)
                    videos_to_save.append(video)

        if len(videos_to_save) > 0:
            Video.objects.bulk_update(videos_to_save, ['status', 'video_id', THUMBNAILS_PATH, TRANSCRIPTS_PATH, TEXT_PATH, LOGOS_PATH])

        if done:
            break

        sleep(TWELVE_LABS_POLL_INTERVAL)

    print(f'Done polling {video_tasks}')


def get_video_data(type, video):
    print(f'Getting {type} for {video.video_id}')

    # This will call the relevant Twelve Labs SDK method based on type:
    # TWELVE_LABS_CLIENT.index.video.transcription(TWELVE_LABS_INDEX_ID, video.video_id)
    # TWELVE_LABS_CLIENT.index.video.text_in_video(TWELVE_LABS_INDEX_ID, video.video_id)
    # TWELVE_LABS_CLIENT.index.video.logo(TWELVE_LABS_INDEX_ID, video.video_id)
    video_data = getattr(TWELVE_LABS_CLIENT.index.video, type)(TWELVE_LABS_INDEX_ID, video.video_id)
    data_json = VideoValueList(root=video_data).model_dump_json(indent=2)
    print(data_json)

    data_path = url_path_join(type, f'{video.video_id}.json')
    print(f'Saving transcript to {data_path}')
    print(f'default_storage: {default_storage}')
    name = default_storage.save(data_path, BytesIO(bytes(data_json, encoding='utf-8')))
    print(f'save() returned {name}')
    setattr(video, type, data_path)


def get_all_video_data(video):
    print(f'Getting thumbnail for {video.video_id}')
    thumbnail_url = TWELVE_LABS_CLIENT.index.video.thumbnail(TWELVE_LABS_INDEX_ID, video.video_id)
    print(f'Got response: {thumbnail_url}')

    url_parts = urlparse(thumbnail_url)
    thumbnail_path = url_path_join(THUMBNAILS_PATH, f'{video.video_id}{Path(url_parts.path).suffix}')

    print(f'Saving {thumbnail_url} to {thumbnail_path}')
    default_storage.save(thumbnail_path, urlopen(thumbnail_url))
    video.thumbnail = thumbnail_path

    for type in [TRANSCRIPTS_PATH, TEXT_PATH, LOGOS_PATH]:
        get_video_data(type, video)



# helper based on https://github.com/transloadit/python-sdk/blob/faf225badafe59c311622ab63610f432aac8a77b/transloadit/assembly.py#L127
def assembly_finished(assembly):
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

    client = TransloadIt.Transloadit(TRANSLOADIT_KEY, TRANSLOADIT_SECRET)

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
