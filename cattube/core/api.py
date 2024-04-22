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
from cattube.core.tasks import poll_video_indexing
from cattube.settings import TL_CLIENT, TWELVE_LABS_INDEX_ID, TRANSLOADIT_SECRET


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def index_videos(request):
    video_names = request.data

    print(f'Indexing videos: {video_names}')

    # Update status for UI
    videos = Video.objects.filter(original__in=video_names)
    for video in videos:
        video.status = 'Sending'
    Video.objects.bulk_update(videos, ['status'])

    # Create a task for each video we want to index
    video_tasks = []
    for video in video_names:
        task = TL_CLIENT.task.create(
            TWELVE_LABS_INDEX_ID,
            url=default_storage.url(video),
            disable_video_stream=True
        )
        video_tasks.append({'video': video, 'task_id': task.id})

    print(f'Created tasks: {video_tasks}')

    # Start a Huey task to poll Twelve Labs for status
    poll_video_indexing(video_tasks)

    return Response(video_tasks)


@never_cache
@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_status(request):
    video_tasks = request.data
    print('Getting status!', video_tasks)
    video_names = [video_task['video'] for video_task in video_tasks]
    videos = Video.objects.filter(original__in=video_names)

    for video_task in video_tasks:
        video = videos.get(original__exact=video_task['video'])
        video_task['status'] = video.status

    print(f'get_status() returning {video_tasks}')

    return Response(video_tasks)


@never_cache
@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def video_detail(_, video_id):
    print(f'Received request for detail on: {video_id}')

    video = get_object_or_404(Video, id=video_id)
    serializer = VideoSerializer(video)
    print(f'Returning : {serializer.data}')
    return Response(serializer.data)


def check_signature(data):
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
    if not check_signature(request.data):
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    serializer = NotificationSerializer(data=request.data)
    if serializer.is_valid():
        print(f'Received notification: {serializer.data}')

        # Remove the path prefixes from the object keys
        assembly = json.loads(serializer.data['transloadit'])

        print(f'Getting video for assembly {assembly["assembly_id"]}')
        video = get_object_or_404(Video, assembly_id=assembly['assembly_id'])
        video.update_with_assembly(assembly)

        return Response(status=status.HTTP_204_NO_CONTENT)

    print(f'Serializer errors: {serializer.errors}')
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
