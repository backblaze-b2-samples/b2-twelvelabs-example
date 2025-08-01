import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from django.views.generic.detail import DetailView, SingleObjectTemplateResponseMixin, SingleObjectMixin
from django.views.generic.edit import CreateView
from django.views.generic.edit import DeleteView
from django.views.generic.list import ListView

from cattube.settings import TWELVE_LABS_CLIENT, TWELVE_LABS_INDEX_ID, POLL_TRANSLOADIT, PAGE_SIZE
from .forms import ResultForm
from .models import Video, SearchResult, add_new_files
from .tasks import poll_video_loading
from .utils import create_signed_transloadit_options


class VideoListView(ListView):
    model = Video
    paginate_by = PAGE_SIZE
    ordering = ['-uploaded_at']

    def get_queryset(self):
        """
        Override default, so we can update the database with any new files in B2.
        """
        add_new_files(self.request.user)
        return super().get_queryset()


def delete_page(page):
    for video in page:
        print(f'Deleting {video.id} from index')
        TWELVE_LABS_CLIENT.index.video.delete(TWELVE_LABS_INDEX_ID, video.id)

def delete_videos():
    videos = TWELVE_LABS_CLIENT.index.video.list_pagination(TWELVE_LABS_INDEX_ID)
    # Strange iterator logic...
    delete_page(videos.data)
    while True:
        try:
            delete_page(next(videos))
        except StopIteration:
            break

@method_decorator(login_required, name='dispatch')
class VideoResetView(ListView):
    def get(self, request, *args, **kwargs):
        # Delete videos from TwelveLabs
        delete_videos()
        # Delete videos from the database
        Video.objects.all().delete()
        # Redirect to home
        return HttpResponseRedirect(reverse('home'))


class VideoSearchView(ListView):
    model = Video
    paginate_by = PAGE_SIZE
    template_name = "core/video_results.html"

    def get_queryset(self):
        """
        Search Twelve Labs for videos matching the query
        """
        query = self.request.GET.get("query", None)

        results = TWELVE_LABS_CLIENT.search.query(
            TWELVE_LABS_INDEX_ID,
            ["visual", "audio"],
            query_text=query,
            group_by="video",
            threshold="high"
        )

        # Search results may be in multiple pages, so we need to loop until we're done retrieving them
        search_data = results.data
        print(f"First page's data: {search_data}")

        search_results = []
        while True:
            # Do a database query to get the videos for each page of results
            video_ids = [group.id for group in search_data]
            videos = Video.objects.filter(video_id__in=video_ids)
            for group in search_data:
                try:
                    search_results.append(SearchResult(video=videos.get(video_id__exact=group.id),
                                                       clip_count=len(group.clips),
                                                       clips=group.clips.model_dump_json()))
                except self.model.DoesNotExist:
                    # There is a video in TwelveLabs, but no corresponding row in the database.
                    # Just report it and carry on.
                    print(f'Video {group.id} is in TwelveLabs, but not in the database')

            # Is there another page?
            try:
                search_data = next(results)
                print(f"Next page's data: {search_data}")
            except StopIteration:
                print("There is no next page in search result")
                break

        return search_results

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get("query", None)
        return context


class VideoResultView(SingleObjectTemplateResponseMixin, SingleObjectMixin, View):
    """
    Drill down into a single search result. Parameters are POSTed to this page, since
    they include the search results for this video.
    """
    model = Video
    template_name = "core/video_result.html"
    pk_url_kwarg = 'id'

    def get_object(self, queryset=None):
        """
        Get the object from the "id" form parameter, referenced here as "pk"
        """
        if queryset is None:
            queryset = self.get_queryset()
        return queryset.get(pk=self.pk)

    # noinspection PyAttributeOutsideInit
    def post(self, request):
        """
        Handle the POST, using a Form to extract the parameters, and populate the context with the search
        results (clips), query, and all the video data.
        """
        form = ResultForm(request.POST)
        if not form.is_valid():
            raise ValidationError("Invalid form", code="invalid")

        self.pk = form.cleaned_data['id']
        self.object = self.get_object()

        context = self.get_context_data(object=self.object)
        context['clips'] = json.loads(form.cleaned_data['clips'])
        context['query'] = form.cleaned_data['query']

        return render(request, self.template_name, context)


class VideoDetailView(DetailView):
    model = Video
    slug_field = 'id'
    slug_url_kwarg = 'video_id'


@method_decorator(login_required, name='dispatch')
class VideoCreateView(CreateView):
    model = Video
    fields = ['title', 'assembly_id']

    def get_success_url(self):
        """
        Go to video detail page on success
        """
        return reverse_lazy('watch', kwargs={'video_id': self.object.id})

    def get_context_data(self, **kwargs):
        """
        Add the TransloadIt params and signature to the context
        """
        context = super().get_context_data(**kwargs)
        notify_url = None if POLL_TRANSLOADIT else self.request.build_absolute_uri(reverse('notification'))
        context.update(create_signed_transloadit_options(notify_url))
        return context

    # noinspection PyAttributeOutsideInit
    def form_valid(self, form):
        form.instance.user = self.request.user
        # Save the new object to the database before kicking off the polling task to avoid race conditions
        response = super().form_valid(form)
        if POLL_TRANSLOADIT:
            poll_video_loading(form.data['assembly_id'])
        return response


@method_decorator(login_required, name='dispatch')
class VideoDeleteView(DeleteView):
    model = Video
    slug_field = 'id'
    slug_url_kwarg = 'video_id'

    def form_valid(self, form):
        """
        Delete the file from B2 as well as the object from the database
        """
        video_name = self.get_object().video.name
        print(f'Deleting: {video_name}')
        default_storage.delete(video_name)
        print(f'Deleted: {video_name}')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('home')
