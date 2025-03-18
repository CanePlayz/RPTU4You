from django.contrib import admin

from .models import *

admin.site.register(Quelle)
admin.site.register(Fachschaft)
admin.site.register(Rundmail)
admin.site.register(InterneWebsite)
admin.site.register(ExterneWebsite)
admin.site.register(Standort)
admin.site.register(Kategorie)
admin.site.register(News)

admin.site.register(User)
