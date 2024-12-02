from django.contrib import admin

from .models import Fachschaft, News, User

admin.site.register(User)
admin.site.register(Fachschaft)
admin.site.register(News)
