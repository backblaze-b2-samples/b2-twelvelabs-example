import json
from time import sleep

from huey.contrib import djhuey as huey
from transloadit import client as TransloadIt

from cattube.core.models import Video
from cattube.settings import TRANSLOADIT_KEY, TRANSLOADIT_SECRET, TL_CLIENT, TWELVE_LABS_POLL_INTERVAL


@huey.db_task()
def poll_video_indexing(video_tasks):
    print(f'Polling Twelve Labs for {video_tasks}')

    # Do a single database query for all the videos we're interested in
    video_names = [video_task['video'] for video_task in video_tasks]
    videos = Video.objects.filter(original__in=video_names)

    while True:
        done = True
        videos_to_save = []

        # Retrieve status for each task we created
        for video_task in video_tasks:
            # What's our current state for this video?
            video = videos.get(original__exact=video_task['video'])

            # Do we still need to retrieve status for this task?
            if video.status != 'Ready':
                task = TL_CLIENT.task.retrieve(video_task['task_id'])
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
                    videos_to_save.append(video)

        if len(videos_to_save) > 0:
            Video.objects.bulk_update(videos_to_save, ['status', 'video_id'])

        if done:
            break

        sleep(TWELVE_LABS_POLL_INTERVAL)

    print(f'Done polling {video_tasks}')


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
            video.update_with_assembly(assembly)
            break

        sleep(1)

    print(f'Done polling {assembly_id}')
