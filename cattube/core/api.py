import hmac
import json

from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, parser_classes, authentication_classes, permission_classes
from rest_framework.parsers import FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cattube.core.models import Video
from cattube.core.serializers import VideoSerializer, NotificationSerializer
from cattube.core.tasks import do_video_indexing
from cattube.settings import TWELVE_LABS_CLIENT, TWELVE_LABS_INDEX_ID, TRANSLOADIT_SECRET


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def index_videos(request):
    print(f'Indexing videos: {request.data}')

    videos = Video.objects.all() if request.data.get('selectedAll') else Video.objects.filter(video__in=request.data.videos);

    # Update status in database so that UI can get it
    video_tasks = []
    for video in videos:
        video.status = 'Sending'
        video_tasks.append({
            'video': video.video.name,
            'status': 'Sending'
        })
    Video.objects.bulk_update(videos, ['status'])

    # Start a Huey task to create indexing tasks and poll Twelve Labs for status
    do_video_indexing(video_tasks)

    return Response(video_tasks)


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def delete_videos(request):
    print(f'Deleting videos: {request.data}')

    videos = Video.objects.all() if request.data.get('selectedAll') else Video.objects.filter(video__in=request.data.videos);

    deleted_video_ids = []
    for video in videos:
        try:
            default_storage.delete(video.video)
            deleted_video_ids.append(video.video_id)
        except:
            print(f'Cannot delete {video.video}')
    Video.objects.filter(video_id__in=deleted_video_ids).delete()
    print(f'Deleted videos: {deleted_video_ids}')

    return Response(deleted_video_ids)


@never_cache
@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_status(request):
    video_tasks = request.data;
    print('Getting status: ', video_tasks)
    video_names = [video_task['video'] for video_task in video_tasks]
    videos = Video.objects.filter(video__in=video_names)

    for video_task in video_tasks:
        video = videos.get(video__exact=video_task['video'])
        video_task['status'] = video.status
        video_task['thumbnail'] = default_storage.url(video.thumbnail.name) if video.thumbnail else None
        video_task['original'] = default_storage.url(video.video.name) if video.video else None

    print(f'Status: {video_tasks}')

    return Response(video_tasks)


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


def check_transloadit_signature(data):
    """
    Based on Node implementation at https://transloadit.com/docs/topics/assembly-notifications/#example
    """
    received_signature = data.get('signature')
    payload = data.get('transloadit')

    if not received_signature or not payload:
        return False

    # If the signature contains a colon, we expect it to be of format `algo:actual_signature`.
    # If there are no colons, we assume it's a legacy signature using SHA-1.
    algo_separator_index = received_signature.find(':')
    algo = 'sha1' if algo_separator_index == -1 else received_signature[0, algo_separator_index]

    calculated_signature = hmac.new(TRANSLOADIT_SECRET.encode('utf-8'),
                                    payload.encode('utf-8'),
                                    algo).hexdigest()

    return calculated_signature == received_signature[algo_separator_index + 1:]


@api_view(['POST'])
@parser_classes([FormParser])
def receive_notification_from_transcoder(request):
    if not check_transloadit_signature(request.data):
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
