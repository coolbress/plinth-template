"""The password checks `createsuperuser` and the password forms run.

The admin is on the public address and nothing slows down someone guessing
at the log-in page, so a short or all-numeric password must not be accepted.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


@pytest.mark.parametrize("password", ["k7#q", "4829175306"], ids=["too-short", "all-numeric"])
def test_a_weak_password_is_refused(password: str) -> None:
    with pytest.raises(ValidationError):
        validate_password(password, User(username="owner"))


def test_a_long_password_is_accepted() -> None:
    validate_password("plinth tulip ledger morning", User(username="owner"))
