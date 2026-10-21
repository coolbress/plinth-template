"""List and write your notes, read and change one.

Every query filters by the logged-in person, so another person's note is
not found (404), never shown or changed.
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .access import members
from .models import Note


def _me(request: HttpRequest) -> User:
    user = request.user
    if not isinstance(user, User):  # the middleware lets only a logged-in person through
        raise PermissionDenied
    return user


@members
def note_list(request: HttpRequest) -> HttpResponse:
    me = _me(request)
    if request.method == "POST":
        text = request.POST.get("text", "").strip()[:200]
        if text:
            note = Note.objects.create(owner=me, text=text)
            return redirect("note", pk=note.pk)
    return render(request, "notes/list.html", {"notes": Note.objects.filter(owner=me)})


@members
def note_detail(request: HttpRequest, pk: int) -> HttpResponse:
    note = get_object_or_404(Note, pk=pk, owner=_me(request))
    if request.method == "POST":
        text = request.POST.get("text", "").strip()[:200]
        if text:
            note.text = text
            note.save(update_fields=["text"])
        return redirect("note", pk=note.pk)
    return render(request, "notes/detail.html", {"note": note})
