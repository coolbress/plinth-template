"""Train the starting model and write what a release publishes.

`python -m <package> train` runs it. The model is scikit-learn's logistic
regression, trained on Fisher's iris measurements (150 flowers, shipped
inside scikit-learn, no personal information), with a quarter of the sample
held out to measure it. Replace `load_sample()` with your own data and the
model with your own; keep the three outputs, which the release workflow
uploads with their checksums (docs/how-to/publish-a-release.md).

The model is saved with skops, never with pickle or joblib: loading a pickle
runs whatever code the file holds, so a downloaded model would be a program.
skops refuses to load a type it was not told to trust.

The card also says how the model was made: the scikit-learn and skops
versions (a skops file is loaded with a compatible scikit-learn), the commit,
the seed and the SHA-256 of the data it learned from (`data_sha256`), which
`metrics.json` carries too. Outside a git repository, such as a fresh render, the commit
row says so; the release workflow refuses a card whose commit is not the
tagged one.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from importlib.metadata import version
from pathlib import Path
from typing import Any

# numpy comes with scikit-learn, which needs it.
import numpy as np
import skops.io
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

#: What one run writes, in the order the release lists them. The release
#: workflow uploads these, an sbom.spdx.json and a SHA256SUMS file.
OUTPUTS = ("model.skops", "metrics.json", "MODEL_CARD.md")

#: The line in MODEL_CARD.md the run replaces with the measured numbers.
RESULTS = "<!-- results: the training run writes the numbers here -->"

#: The seed of every random choice in a run: the same code, data and seed
#: give the same model.
SEED = 0

#: The commit row outside a git repository.
NO_COMMIT = "none: not a git repository"

#: The key of the data's SHA-256 in `metrics.json` and in the card. Every
#: other value in `metrics.json` is a number; the release workflow accepts
#: this one key as text, and does not require it.
DATA_SHA256 = "data_sha256"


def load_sample() -> tuple[Any, Any]:
    """The rows to learn from and their answers."""
    features, labels = load_iris(return_X_y=True)
    return features, labels


def data_sha256(*arrays: Any) -> str:
    """The SHA-256 of the data a run learns from, as `load_sample()` returns it.

    What is hashed is the arrays in memory, not files: for each array in
    order, its dtype, its shape and its bytes in C order. The same rows give
    the same hash wherever they were read from; one changed value, one row
    more or less, or another order gives another. A list or a DataFrame is
    hashed as `numpy.asarray` makes it. Arrays of Python objects (text
    columns, mixed types) are refused: their bytes are memory addresses,
    which change every run; encode them as numbers first, or hash the files
    they were read from instead.
    """
    digest = hashlib.sha256()
    for array in arrays:
        a = np.ascontiguousarray(np.asarray(array))
        if a.dtype.hasobject:
            raise TypeError(f"cannot hash an array of Python objects ({a.dtype}): encode it first")
        digest.update(f"{a.dtype.str}{a.shape};".encode())
        digest.update(a.tobytes())
    return digest.hexdigest()


def source_commit(where: Path) -> str:
    """The commit checked out at `where`, or NO_COMMIT outside a git repository."""
    # The arguments are literals; git lives in different places on CI and on
    # a laptop, so it is found on PATH (S607).
    done = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        cwd=where,
        # The skip below matches git's English message (tests/test_tree_hygiene.py).
        env={**os.environ, "LC_ALL": "C"},
    )
    if done.returncode == 0:
        return done.stdout.strip()
    # Only the fresh render is recorded as having no commit. Anything else,
    # such as a repository with no commit yet, stops the run with git's words.
    if "not a git repository" in done.stderr.lower():
        return NO_COMMIT
    raise RuntimeError(f"`git rev-parse HEAD` failed: {done.stderr.strip()}")


def made_with(where: Path) -> dict[str, str]:
    """How a run was made: what loading the model needs, and what repeats it."""
    return {
        "scikit-learn": version("scikit-learn"),
        "skops": version("skops"),
        "commit": source_commit(where),
        "seed": str(SEED),
    }


def _table(heading: str, rows: dict[str, Any]) -> str:
    return "\n".join(
        [f"| {heading} | Value |", "|---|---|", *(f"| `{k}` | {v} |" for k, v in rows.items())]
    )


def train(out: Path, card: Path) -> dict[str, float | str]:
    """Train, measure on the held-out part, and write OUTPUTS into `out`.

    The card is read from `card` and written to `out` with its results line
    replaced by the metrics and by how the run was made (`made_with`, the
    commit read from the working directory, and the data's SHA-256); the
    committed card is left as it is. `metrics.json` holds the measures and,
    under DATA_SHA256, the same hash.
    """
    template = card.read_text(encoding="utf-8")
    if RESULTS not in template:
        raise ValueError(f"{card} has no results line to fill: {RESULTS}")
    made = made_with(Path.cwd())
    features, labels = load_sample()
    made[DATA_SHA256] = data_sha256(features, labels)
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=SEED, stratify=labels
    )
    model = LogisticRegression(max_iter=1000, random_state=SEED).fit(x_train, y_train)
    predicted = model.predict(x_test)
    measures: dict[str, float] = {
        "accuracy": round(float(accuracy_score(y_test, predicted)), 4),
        "f1_macro": round(float(f1_score(y_test, predicted, average="macro")), 4),
        "rows_trained": len(y_train),
        "rows_held_out": len(y_test),
    }
    metrics: dict[str, float | str] = {**measures, DATA_SHA256: made[DATA_SHA256]}
    out.mkdir(parents=True, exist_ok=True)
    skops.io.dump(model, out / "model.skops")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    results = f"{_table('Measure', measures)}\n\n{_table('How it was made', made)}"
    (out / "MODEL_CARD.md").write_text(template.replace(RESULTS, results), encoding="utf-8")
    return metrics
