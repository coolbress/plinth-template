"""URL routes."""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path


def healthz(request: HttpRequest) -> HttpResponse:
    """Answers without touching the database: the image check and the host ask it."""
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz),
]
