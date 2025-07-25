from django.contrib import admin
from django.urls import path
from news.views import receive_news, views

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # News
    path("news/", views.news_view, name="news"),
    path("news/partial/", views.news_partial, name="news_partial"),
    path("news/<int:pk>/", views.news_detail, name="news_detail"),
    path("foryoupage/", views.foryoupage, name="foryoupage"),
    # API
    path("api/news/", receive_news.ReceiveNews.as_view(), name="receive_news"),
    path("api/news/rundmail/date", views.request_date, name="request_date"),
    # User
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("preferences/", views.update_preferences, name="preferences"),
    path("account/", views.account_view, name="account"),
    # Kalender
    path("kalender/", views.calendar_page, name="calendar_page"),
    path("api/calendar-events/", views.calendar_events, name="calendar_events"),
    path(
        "api/calendar-events/<int:event_id>/",
        views.calendar_event_detail,
        name="calendar_event_detail",
    ),
    path("kalender/import/", views.import_ics, name="import_ics"),
    path("kalender/export/", views.export_ics, name="export_ics"),
    # Sonstiges
    path("links/", views.links, name="links"),
    path("db-connections/", views.db_connection_status),
    path("health/", views.health_check, name="health_check"),
]
