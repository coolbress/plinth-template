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
"""

from __future__ import annotations

import json
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


def load_sample() -> tuple[Any, Any]:
    """The rows to learn from and their answers."""
    features, labels = load_iris(return_X_y=True)
    return features, labels


def train(out: Path, card: Path) -> dict[str, float]:
    """Train, measure on the held-out part, and write OUTPUTS into `out`.

    The card is read from `card` and written to `out` with its results line
    replaced; the committed card is left as it is.
    """
    template = card.read_text(encoding="utf-8")
    if RESULTS not in template:
        raise ValueError(f"{card} has no results line to fill: {RESULTS}")
    features, labels = load_sample()
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=0, stratify=labels
    )
    model = LogisticRegression(max_iter=1000).fit(x_train, y_train)
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
    table = "\n".join(
        ["| Measure | Value |", "|---|---|", *(f"| `{k}` | {v} |" for k, v in metrics.items())]
    )
    (out / "MODEL_CARD.md").write_text(template.replace(RESULTS, table), encoding="utf-8")
    return metrics
