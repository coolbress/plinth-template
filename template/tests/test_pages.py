"""What the pages carry for a screen reader, checked on the HTML Django serves.

axe-core, which `ci / web-audit` runs, reports a page with no `lang`, content
outside a `<main>` landmark, or a field with no label. These read the same
three facts from the served page, so a template that drops one fails here
before a browser opens it.
"""

from __future__ import annotations

import secrets
from html.parser import HTMLParser

import pytest
from django.contrib.auth.models import User
from django.test import Client

#: What may sit outside `<main>`: the document's own head.
HEAD = {"html", "head", "title", "meta", "link"}


class Page(HTMLParser):
    """The `lang` on `<html>`, how many `<main>`, what sits outside it, and
    which fields have no label."""

    def __init__(self, html: str) -> None:
        super().__init__()
        self.lang = ""
        self.mains = 0
        self.depth = 0
        self.outside: list[str] = []
        self.fields: dict[str, str] = {}
        self.labelled: set[str] = set()
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "main":
            self.mains += 1
            self.depth += 1
        elif not self.depth and tag not in HEAD:
            self.outside.append(tag)
        if tag == "label" and a.get("for"):
            self.labelled.add(a["for"])
        if tag in ("input", "textarea", "select") and a.get("type") not in ("hidden", "submit"):
            self.fields[a.get("name", "?")] = a.get("id", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "main":
            self.depth -= 1

    def unlabelled(self) -> list[str]:
        return [name for name, id_ in self.fields.items() if not id_ or id_ not in self.labelled]


def check(html: str) -> None:
    page = Page(html)
    assert page.lang, "<html> has no lang attribute"
    assert page.mains == 1, f"{page.mains} <main> elements, not one"
    assert page.outside == [], f"outside <main>: {page.outside}"
    assert page.fields, "no field on the page"
    assert page.unlabelled() == [], f"fields with no <label for>: {page.unlabelled()}"


def test_the_log_in_page(client: Client) -> None:
    check(client.get("/accounts/login/", secure=True).content.decode())


@pytest.mark.django_db
def test_the_notes_page_and_a_note(client: Client) -> None:
    client.force_login(User.objects.create_user("dana", password=secrets.token_urlsafe()))
    check(client.get("/", secure=True).content.decode())
    written = client.post("/", {"text": "buy bread"}, secure=True)
    assert written.status_code == 302
    check(client.get(written["Location"], secure=True).content.decode())


FIELD = '<label for="n">Note</label><input id="n" name="text">'
WHOLE = f'<html lang="en"><title>t</title><main>{FIELD}</main>'


def test_a_whole_page_passes() -> None:
    check(WHOLE)


@pytest.mark.parametrize(
    ("html", "missing"),
    [
        (WHOLE.replace(' lang="en"', ""), "lang"),
        (WHOLE.replace("<main>", "").replace("</main>", ""), "<main>"),
        (WHOLE.replace("<main>", "<h1>Notes</h1><main>"), "outside"),
        (WHOLE.replace('<label for="n">Note</label>', ""), "label"),
        (WHOLE.replace(' for="n"', ""), "label"),
    ],
)
def test_a_page_missing_one_fails(html: str, missing: str) -> None:
    with pytest.raises(AssertionError, match=missing):
        check(html)
