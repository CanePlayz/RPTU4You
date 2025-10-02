from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path

from news.views.account import (
    account_view,
    login_view,
    logout_view,
    register_view,
    update_preferences,
)
from news.views.calendar import (
    calendar_event_detail,
    calendar_events,
    calendar_page,
    export_ics,
    import_ics,
)
from news.views.news import (
    foryoupage,
    links,
    news_detail,
    news_partial,
    news_view,
)
from news.views.receive_news import ReceiveNews
from news.views.system import (
    db_connection_status,
    health_check,
    request_date,
    set_language,
)

# Sprachunabhängige URLs
urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API
    path("api/news/", ReceiveNews.as_view(), name="receive_news"),
    path("api/news/rundmail/date", request_date, name="request_date"),
    # Kalender
    path("api/calendar-events/", calendar_events, name="calendar_events"),
    path(
        "api/calendar-events/<int:event_id>/",
        calendar_event_detail,
        name="calendar_event_detail",
    ),
    path("kalender/import/", import_ics, name="import_ics"),
    path("kalender/export/", export_ics, name="export_ics"),
]

urlpatterns += i18n_patterns(
    path("set-language/", set_language, name="set_language"),
    # Admin URLs
    # News
    path("", news_view, name="News"),
    path("news/", news_view, name="news"),
    path("news/partial/", news_partial, name="news_partial"),
    path("news/<int:pk>/", news_detail, name="news_detail"),
    path("foryoupage/", foryoupage, name="foryoupage"),
    # User
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("register/", register_view, name="register"),
    path("preferences/", update_preferences, name="preferences"),
    path("account/", account_view, name="account"),
    # Kalender
    path("kalender/", calendar_page, name="calendar_page"),
    path("api/calendar-events/", calendar_events, name="calendar_events"),
    path(
        "api/calendar-events/<int:event_id>/",
        calendar_event_detail,
        name="calendar_event_detail",
    ),
    path("kalender/import/", import_ics, name="import_ics"),
    path("kalender/export/", export_ics, name="export_ics"),
    # Sonstiges
    path("links/", links, name="links"),
    path("db-connections/", db_connection_status),
    path("health/", health_check, name="health_check"),
)
