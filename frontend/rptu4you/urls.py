"""
URL configuration for rptu4you project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from rptu4you.news.views import receive_news, views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/news", receive_news.ReceiveNews.as_view(), name="receive_news"),
    path("api/news/paginated", views.paginated_news, name="paginated_news"),
    path("api/news/rundmail/date", views.request_date, name="request_date"),
    path("News/", views.news_view, name="News"),
    path("news/<int:news_id>/", views.news_detail, name="news_detail"),
    path("", views.news_view, name="News"),
    path("Links/", views.Links, name="Links"),
    path("ForYouPage/", views.ForYouPage, name="ForYouPage"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("preferences/", views.update_preferences, name="preferences"),
    path("account/", views.account_view, name="account"),
    # Kalender URLs
    path("kalender/", views.calendar_page, name="calendar_page"),
    path("api/calendar-events/", views.calendar_events, name="calendar_events"),
    path(
        "api/calendar-events/<int:event_id>/",
        views.calendar_event_detail,
        name="calendar_event_detail",
    ),
    path(
        "api/calendar-events/<int:event_id>/unhide/",
        views.unhide_event,
        name="unhide_event",
    ),
    path("kalender/import/", views.import_ics, name="import_ics"),
    path("kalender/export/", views.export_ics, name="export_ics"),
]
