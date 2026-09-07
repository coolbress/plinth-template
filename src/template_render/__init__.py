"""Render this template for real and return the result.

Reading copier.yml and checking that it looks right is not the same as
rendering it: an earlier generation of this repository did only the former
and missed both a missing `.copier-answers.yml` and a symlink turned into a
copy, while every render succeeded.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

# src/template_render/__init__.py -> src/template_render -> src -> repository root
TEMPLATE_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_ANSWERS: dict[str, Any] = {
    "project_name": "probe",
    "license": "MIT",
    "archetype": "cli",
}


def render(dest: Path, **answers: Any) -> Path:
    """Render the template into `dest` and return that path.

    `vcs_ref="HEAD"`: even for a local path, copier picks the latest tag of a
    git repository, which would test the last release instead of the working
    tree.
    """
    import copier
    from copier.errors import DirtyLocalWarning, ShallowCloneWarning

    data = dict(DEFAULT_ANSWERS)
    data.update(answers)
    # Under `filterwarnings = ["error"]` exactly two warnings are let through:
    # DirtyLocalWarning (a dirty working tree is rendered as is, which is the
    # point: the template being edited is the one under test) and
    # ShallowCloneWarning (actions/checkout clones with depth 1, and HEAD needs
    # no history).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DirtyLocalWarning)
        warnings.simplefilter("ignore", ShallowCloneWarning)
        copier.run_copy(
            str(TEMPLATE_ROOT),
            str(dest),
            data=data,
            defaults=True,
            quiet=True,
            unsafe=False,
            vcs_ref="HEAD",
        )
    return dest
