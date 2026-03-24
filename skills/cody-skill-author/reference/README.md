# Reference copies of Cody docs

These files are **mirrors** of the canonical markdown under the Cody repository’s `docs/` directory. After editing `docs/*.md`, run `scripts/sync_reference_docs.py` (via `run_skill` or from the repo with `PYTHONPATH` set) to refresh them.

## Resolving links

Links like `[foo](../utils/bar.py)` were written for paths **relative to `docs/`**. From the repository root, resolve `../utils/bar.py` as `utils/bar.py` (i.e. drop the leading `../` from the `docs/` parent). Same for `../components/`, `../examples/`, `../main.py`, etc.

Cross-links between these files (`extending_cody.md`, `utils_reference.md`, `password_vault.md`) still work as normal here.
