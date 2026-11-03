# Data

Nothing in this folder is committed but this file and `.gitignore`. Data is
large, it changes outside the code, and it can hold personal information that
a commit would keep in the history for good.

| Folder | What goes in it | Committed |
|---|---|---|
| `raw/` | The data as you received it. Never edit it; a mistake there cannot be undone. | No |
| `processed/` | What the code makes from `raw/`. Delete it any time and run the code again. | No |
| this `README.md` | Where each file in `raw/` came from, its licence, the date it was fetched, and whether it holds personal information. | Yes |

A new person on the project gets the data from where this file says, not from
git. Write that down for every file you add to `raw/`:

- **`raw/<file>`**: where it came from (a link or the person who gave it),
  its licence, the date it was fetched, and whether it holds personal
  information. `MODEL_CARD.md` asks the same question of the training data.

The sample model in `src/` uses a dataset that ships with scikit-learn, so
this folder starts empty.
