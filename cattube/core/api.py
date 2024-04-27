import json
import traceback

from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, parser_classes, authentication_classes, permission_classes
from rest_framework.parsers import FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from twelvelabs import NotFoundError

from cattube.core.models import Video
from cattube.core.serializers import VideoSerializer, NotificationSerializer
from cattube.core.tasks import do_video_indexing
from cattube.core.utils import verify_transloadit_signature
from cattube.settings import TWELVE_LABS_CLIENT, TWELVE_LABS_INDEX_ID


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def index_videos(request):
    print(f'Indexing videos: {request.data}')

    if request.data.get('selectedAll'):
        videos = Video.objects.all()
    else:
        videos = Video.objects.filter(id__in=request.data['videos'])

    # Don't index videos that have already been submitted for indexing
    videos = videos.filter(status__in=['', 'Sending'])

    # Update status in database so that UI can get it
    video_dicts = []
    for video in videos:
        video.status = 'Sending'
        video_dicts.append({
            'id': video.id,
            'video': video.video.name,
            'status': 'Sending'
        })
    Video.objects.bulk_update(videos, ['status'])

    # Start a Huey task to create indexing tasks and poll Twelve Labs for status
    do_video_indexing(video_dicts)

    return Response(video_dicts)


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def delete_videos(request):
    """
    Delete videos with ids listed in request.data. We try deleting from the B2 storage first, then from the Twelve Labs
    index, then from the database. At each step, we don't care if it's already been deleted.
    """
    print(f'Deleting videos: {request.data}')

    if request.data.get('selectedAll'):
        videos = Video.objects.all()
    else:
        videos = Video.objects.filter(id__in=request.data['videos'])

    # Try deleting from B2 first
    deleted_from_storage = []
    file_fields = ['video', 'thumbnail', 'transcription', 'text_in_video', 'logo']
    for video in videos:
        deletion_failed = False
        for attr in file_fields:
            name = getattr(video, attr).name
            if name:
                try:
                    default_storage.delete(name)
                    setattr(video, attr, None)
                except Exception as err:
                    print(f'Cannot delete {name} from storage: {err}')
                    traceback.print_exception(type(err), err, err.__traceback__)
                    deletion_failed = True
        if not deletion_failed:
            deleted_from_storage.append(video)

    print(f'Deleted from storage: {deleted_from_storage}')
    Video.objects.bulk_update(deleted_from_storage, ['video'])

    # Now delete from Twelve Labs
    deleted_from_index = []
    file_fields = ['thumbnail', 'transcription', 'text_in_video', 'logo']
    for video in deleted_from_storage:
        try:
            try:
                TWELVE_LABS_CLIENT.index.video.delete(TWELVE_LABS_INDEX_ID, video.video_id)
                video.video_id = ''
                for attr in file_fields:
                    setattr(video, attr, None)
            except NotFoundError:
                print(f'{video.video_id} not found in index. Carrying on anyway.')

            deleted_from_index.append(video)
        except Exception as err:
            print(f'Cannot delete {video.video_id} from index: {err}')
            traceback.print_exception(type(err), err, err.__traceback__)

    fields_to_update = file_fields
    fields_to_update.append('video_id')

    print(f'Deleted from index: {deleted_from_index}')
    Video.objects.bulk_update(deleted_from_index, fields_to_update)

    # Now delete from the database
    ids_for_deletion = [video.id for video in deleted_from_index]
    print(f'Deleting ids: {ids_for_deletion}')
    deleted, rows_count = Video.objects.filter(id__in=ids_for_deletion).delete()
    print(f'Deleted {deleted} objects from database: {rows_count}')

    return Response([video.id for video in deleted_from_index])


@never_cache
@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_status(request):
    """
    Query the database for the status of the videos passed in request.data.
    """
    video_dicts = request.data
    print('Getting status: ', video_dicts)
    video_ids = [video_dict['id'] for video_dict in video_dicts]
    videos = Video.objects.filter(id__in=video_ids)

    for video_dict in video_dicts:
        video = videos.get(id__exact=video_dict['id'])
        video_dict['status'] = video.status
        video_dict['thumbnail'] = default_storage.url(video.thumbnail.name) if video.thumbnail else None
        video_dict['original'] = default_storage.url(video.video.name) if video.video else None

    print(f'Status: {video_dicts}')

    return Response(video_dicts)


@never_cache
@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def video_detail(_, video_id):
    print(f'Getting detail: {video_id}')
    video = get_object_or_404(Video, id=video_id)
    serializer = VideoSerializer(video)
    print(f'Returning : {serializer.data}')
    return Response(serializer.data)


@api_view(['POST'])
@parser_classes([FormParser])
def receive_notification_from_transcoder(request):
    if not verify_transloadit_signature(request.data):
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    serializer = NotificationSerializer(data=request.data)
    if serializer.is_valid():
        print(f'Received notification: {serializer.data}')

        # Remove the path prefixes from the object keys
        assembly = json.loads(serializer.data['transloadit'])

        print(f'Getting video for assembly {assembly["assembly_id"]}')
        video = get_object_or_404(Video, assembly_id=assembly['assembly_id'])
        video.update_from_assembly(assembly)

        return Response(status=status.HTTP_204_NO_CONTENT)

    print(f'Serializer errors: {serializer.errors}')
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
