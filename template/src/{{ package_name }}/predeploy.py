"""The pre-deploy step: `python -m <package>.predeploy`, what `render.yaml` runs.

It waits for the database to accept a connection, then applies the
migrations once. On the first deploy Render creates the database and the web
service together, and the step can start before the database is up; a bare
`migrate` then fails with "Connection refused" and the first deploy is red.

Only the connection is retried, every few seconds for up to two minutes.
`migrate` itself is never retried: a migration that fails stops the deploy,
and the running version keeps serving. A database that never answers is
still a failed deploy, with the last connection error in the log.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from collections.abc import Callable

from django.db.utils import OperationalError

LIMIT_SECONDS = 120.0
INTERVAL_SECONDS = 5.0

log = logging.getLogger(__name__)


def run(
    connect: Callable[[], None],
    migrate: Callable[[], None],
    *,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    limit: float = LIMIT_SECONDS,
    interval: float = INTERVAL_SECONDS,
) -> int:
    """Call `connect` until it stops raising `OperationalError` or `limit` passes,
    then `migrate` once. The exit code: 0 once migrated, 1 when the database
    never answered."""
    deadline = clock() + limit
    attempt = 0
    while True:
        attempt += 1
        try:
            connect()
            break
        except OperationalError as error:
            left = deadline - clock()
            if left <= 0:
                log.error("database not reachable after %d attempts: %s", attempt, error)
                return 1
            log.info("database not ready (attempt %d): %s", attempt, error)
            sleep(min(interval, left))
    migrate()
    return 0


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"{__package__}.settings")
    import django

    django.setup()
    from django.core.management import call_command
    from django.db import connection

    from .__main__ import configure

    configure()

    def connect() -> None:
        try:
            connection.ensure_connection()
        except OperationalError:
            # A refused attempt leaves nothing to reuse; the next one starts clean.
            connection.close()
            raise

    def migrate() -> None:
        call_command("migrate", interactive=False)

    sys.exit(run(connect, migrate))


if __name__ == "__main__":
    main()
