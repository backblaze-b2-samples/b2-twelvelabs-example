from django.contrib.auth import views as auth_views
from django.urls import path

import cattube.core.api
from cattube.core import views

urlpatterns = [
    # Website
    path('', views.VideoListView.as_view(), name='home'),
    path('search', views.VideoSearchView.as_view(), name='search'),
    path('login', auth_views.LoginView.as_view(), name='login'),
    path('logout', auth_views.LogoutView.as_view(), name='logout'),
    path('upload', views.VideoCreateView.as_view(), name='upload'),

    path('videos/<str:video_id>', views.VideoDetailView.as_view(), name='watch'),
    path('videos/delete/<str:video_id>', views.VideoDeleteView.as_view(), name='delete'),

    # REST API
    path('api/videos/index_videos', cattube.core.api.index_videos),
    path('api/videos/get_status', cattube.core.api.get_status),
    path('api/videos/', cattube.core.api.receive_notification_from_transcoder, name='notification'),
    path('api/videos/<str:video_id>', cattube.core.api.video_detail, name='video_detail'),
]
