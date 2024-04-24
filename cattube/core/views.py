import hashlib
import hmac
import json
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.generic.base import View
from django.views.generic.detail import DetailView, SingleObjectTemplateResponseMixin, SingleObjectMixin
from django.views.generic.edit import CreateView
from django.views.generic.edit import DeleteView
from django.views.generic.list import ListView

from cattube.settings import TWELVE_LABS_CLIENT, TWELVE_LABS_INDEX_ID, POLL_TRANSLOADIT, VIDEOS_PATH, TRANSCRIPTS_PATH
from .forms import ResultForm
from .models import Video, SearchResult, SearchDataList
from .tasks import poll_video_loading
from .utils import url_path_join

PAGE_SIZE = 12


def add_new_files(view):
    if view.request.user.is_authenticated:
        directories, files = default_storage.listdir(f'{VIDEOS_PATH}')
        videos = Video.objects.all()
        new_videos = []
        for file in files:
            path_to_file = url_path_join(VIDEOS_PATH, file)
            if len(videos.filter(video__exact=path_to_file)) == 0:
                new_videos.append(Video(
                    video=path_to_file,
                    title=Path(file).stem,
                    user=view.request.user,
                    uploaded_at=default_storage.get_modified_time(path_to_file)))
        if len(new_videos) > 0:
            Video.objects.bulk_create(new_videos)


class VideoListView(ListView):
    model = Video
    paginate_by = PAGE_SIZE
    ordering = ['-uploaded_at']

    def get_queryset(self):
        add_new_files(self)
        return super().get_queryset()


class VideoSearchView(ListView):
    model = Video
    paginate_by = PAGE_SIZE
    template_name = "core/video_results.html"

    def get_queryset(self):
        query = self.request.GET.get("query", None)

        # Search indexed videos for the query string
        result = TWELVE_LABS_CLIENT.search.query(
            TWELVE_LABS_INDEX_ID,
            query,
            ["visual", "conversation", "text_in_video", "logo"],
            group_by="video",
            threshold="medium"
        )

        # Search results may be in multiple pages, so we need to loop until we're done retrieving them
        search_data = result.data
        print(f"First page's data: {search_data}")

        search_results = []
        while True:
            # Do a database query to get the videos for each page of results
            video_ids = [group.id for group in search_data]
            videos = Video.objects.filter(video_id__in=video_ids)
            search_results += [SearchResult(video=videos.get(video_id__exact=group.id),
                                            clip_count=len(group.clips),
                                            clips=SearchDataList(root=group.clips).model_dump_json()) for group in search_data]

            # Is there another page?
            try:
                search_data = next(result)
                print(f"Next page's data: {search_data}")
            except StopIteration:
                print("There is no next page in search result")
                break

        return search_results

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get("query", None)
        return context


def load_json(object, type):
    object.transcription.open(mode="rb")
    data = getattr(object, type).read()
    object.transcription.close()

    return json.loads(data)

class VideoDetailView(DetailView):
    model = Video
    slug_field = 'id'
    slug_url_kwarg = 'video_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transcription'] = load_json(self.object, TRANSCRIPTS_PATH)
        return context

@method_decorator(login_required, name='dispatch')
class VideoCreateView(CreateView):
    model = Video
    fields = ['title', 'assembly_id', ]

    def get_success_url(self):
        return reverse_lazy('watch', kwargs={'video_id': self.object.id})

    def get_context_data(self, **kwargs):
        # Signature calculation from
        # https://transloadit.com/docs/topics/signature-authentication/#signature-python-sdk-demo
        expires = (timedelta(seconds=60 * 60) + datetime.utcnow()).strftime("%Y/%m/%d %H:%M:%S+00:00")
        params = {
            'auth': {
                'key': settings.TRANSLOADIT_KEY,
                'expires': expires,
            },
            'template_id': settings.TRANSLOADIT_TEMPLATE_ID,
        }

        if not POLL_TRANSLOADIT:
            params['notify_url'] = self.request.build_absolute_uri(reverse('notification'))

        message = json.dumps(params, separators=(',', ':'), ensure_ascii=False)
        signature = hmac.new(settings.TRANSLOADIT_SECRET.encode('utf-8'),
                             message.encode('utf-8'),
                             hashlib.sha384).hexdigest()

        context = super().get_context_data(**kwargs)
        # Need to mark message as safe so Django doesn't escape the JSON
        context['params'] = mark_safe(message)
        context['signature'] = 'sha384:' + signature
        return context

    # noinspection PyAttributeOutsideInit
    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        if POLL_TRANSLOADIT:
            poll_video_loading(form.data['assembly_id'])
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class VideoDeleteView(DeleteView):
    model = Video
    slug_field = 'id'
    slug_url_kwarg = 'video_id'

    def form_valid(self, form):
        video = self.get_object().video
        print(f'Deleting: {video}')
        default_storage.delete(video.name)
        print(f'Deleted: {video}')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('home')


class VideoResultView(SingleObjectTemplateResponseMixin, SingleObjectMixin, View):
    model = Video
    template_name = "core/video_result.html"
    pk_url_kwarg = 'id'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        return queryset.get(pk=self.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clips'] = json.loads(self.request.POST.get('clips', None))
        context['query'] = self.request.POST.get('query', None)
        context['transcription'] = load_json(self.object, TRANSCRIPTS_PATH)
        return context

    def post(self, request):
        form = ResultForm(request.POST)
        if form.is_valid():
            self.pk = form.cleaned_data['id']
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
        else:
            # TBD
            print('INVALID')
        return render(request, self.template_name, context)
