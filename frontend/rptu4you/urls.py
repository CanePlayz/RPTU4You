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
    path("News/", views.News, name="News"),
    path("", views.News, name="News"),
    path("Links/", views.Links, name="Links"),
    path("ForYouPage/", views.ForYouPage, name="ForYouPage"),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('preferences/', views.update_preferences, name='preferences'),
]
