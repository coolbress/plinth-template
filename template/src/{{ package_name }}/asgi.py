"""The ASGI application the server runs."""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"{__package__}.settings")

application = get_asgi_application()
