"""URL routes. Each view is marked public or for logged-in people (notes/access.py)."""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import views as auth
from django.http import HttpRequest, HttpResponse
from django.urls import path

from .notes import views as notes
from .notes.access import members, public


@public
def healthz(request: HttpRequest) -> HttpResponse:
    """Answers without touching the database: the image check and the host ask it."""
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    # The admin checks its own staff permission on every page but its log-in.
    path("admin/", admin.site.urls),
    path("healthz", healthz),
    path("accounts/login/", public(auth.LoginView.as_view()), name="login"),
    path("accounts/logout/", members(auth.LogoutView.as_view()), name="logout"),
    path("", notes.note_list, name="notes"),
    path("notes/<int:pk>/", notes.note_detail, name="note"),
]
