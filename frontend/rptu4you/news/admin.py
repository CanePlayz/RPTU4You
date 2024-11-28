from django.contrib import admin
from .models import User, Fachschaft, News, NewsCategory

admin.site.register(User)
admin.site.register(Fachschaft)
admin.site.register(News)
admin.site.register(NewsCategory)
