"""This project's own user model.

It adds nothing to Django's `AbstractUser` yet. It is here from the first
migration because Django cannot change the user model of a database that
already has one: with it, a field added to users later is an ordinary
migration. `AUTH_USER_MODEL` in the settings names it.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """A person who can log in."""
