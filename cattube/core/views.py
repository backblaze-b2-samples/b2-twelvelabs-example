import hashlib
import hmac
import json
from datetime import datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic.edit import DeleteView
from django.views.generic.list import ListView

from cattube.settings import TL_CLIENT, TWELVE_LABS_INDEX_ID, POLL_TRANSLOADIT
from .models import Video, SearchResult
from .tasks import poll_video_loading


# From https://codereview.stackexchange.com/a/24416/27914
def url_path_join(*parts):
    """Normalize url parts and join them with a slash."""
    schemes, netlocs, paths, queries, fragments = zip(*(urlsplit(part) for part in parts))
    scheme = first(schemes)
    netloc = first(netlocs)
    path = '/'.join(x.strip('/') for x in paths if x)
    query = first(queries)
    fragment = first(fragments)
    return urlunsplit((scheme, netloc, path, query, fragment))


def first(sequence, default=''):
    return next((x for x in sequence if x), default)


class VideoListView(ListView):
    model = Video
    paginate_by = 12
    ordering = ['-uploaded_at']


class VideoSearchView(ListView):
    model = Video
    paginate_by = 2
    template_name = "core/video_results.html"

    def get_queryset(self):
        query = self.request.GET.get("query", None)

        # Search indexed videos for the query string
        result = TL_CLIENT.search.query(
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
            search_results += [SearchResult(video=videos.get(video_id__exact=group.id), group=group) for group in search_data]

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


class VideoDetailView(DetailView):
    model = Video
    slug_field = 'id'
    slug_url_kwarg = 'video_id'


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

    def get_success_url(self):
        return reverse('home')
