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
versions (a skops file is loaded with a compatible scikit-learn), the commit
and the seed. Outside a git repository, such as a fresh render, the commit
row says so; the release workflow refuses a card whose commit is not the
tagged one.
"""

from __future__ import annotations

import json
import os
import subprocess
from importlib.metadata import version
from pathlib import Path
from typing import Any

import skops.io
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

#: What one run writes, in the order the release lists them. The release
#: workflow uploads exactly these and a SHA256SUMS file.
OUTPUTS = ("model.skops", "metrics.json", "MODEL_CARD.md")

#: The line in MODEL_CARD.md the run replaces with the measured numbers.
RESULTS = "<!-- results: the training run writes the numbers here -->"

#: The seed of every random choice in a run: the same code, data and seed
#: give the same model.
SEED = 0

#: The commit row outside a git repository.
NO_COMMIT = "none: not a git repository"


def load_sample() -> tuple[Any, Any]:
    """The rows to learn from and their answers."""
    features, labels = load_iris(return_X_y=True)
    return features, labels


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


def train(out: Path, card: Path) -> dict[str, float]:
    """Train, measure on the held-out part, and write OUTPUTS into `out`.

    The card is read from `card` and written to `out` with its results line
    replaced by the metrics and by how the run was made (`made_with`, the
    commit read from the working directory); the committed card is left as
    it is.
    """
    template = card.read_text(encoding="utf-8")
    if RESULTS not in template:
        raise ValueError(f"{card} has no results line to fill: {RESULTS}")
    made = made_with(Path.cwd())
    features, labels = load_sample()
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=SEED, stratify=labels
    )
    model = LogisticRegression(max_iter=1000, random_state=SEED).fit(x_train, y_train)
    predicted = model.predict(x_test)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, predicted)), 4),
        "f1_macro": round(float(f1_score(y_test, predicted, average="macro")), 4),
        "rows_trained": len(y_train),
        "rows_held_out": len(y_test),
    }
    out.mkdir(parents=True, exist_ok=True)
    skops.io.dump(model, out / "model.skops")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    results = f"{_table('Measure', metrics)}\n\n{_table('How it was made', made)}"
    (out / "MODEL_CARD.md").write_text(template.replace(RESULTS, results), encoding="utf-8")
    return metrics
