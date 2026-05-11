from django.contrib import admin
from .models import Gender, UserProfile

# This makes your tables show up in the Admin Dashboard
admin.site.register(Gender)
admin.site.register(UserProfile)