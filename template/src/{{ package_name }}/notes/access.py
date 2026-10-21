"""Every route is marked: public, or for people who are logged in.

`LoginRequiredMiddleware` already sends an anonymous request to the log-in
page unless its view is marked public. The mark makes the choice visible in
the code, and `tests/test_access.py` fails on a route that has neither, so a
new route cannot be added without deciding. This is plinth's proposal, not a
published standard.
"""

from __future__ import annotations

from collections.abc import Callable

from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponseBase


def public[View: Callable[..., HttpResponseBase]](view: View) -> View:
    """Anyone may ask, logged in or not."""
    return login_not_required(view)


def members[View: Callable[..., HttpResponseBase]](view: View) -> View:
    """Only a logged-in person; the middleware sends anyone else to log in."""
    view.login_required = True  # type: ignore[attr-defined]
    return view
