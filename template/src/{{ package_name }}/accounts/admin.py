"""Users in the admin, with Django's own forms for them."""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

admin.site.register(User, UserAdmin)
