# /verify

Run quality checks before committing or opening a PR.

## Modes

- `quick` — Lint + type check
- `full` — Lint + type check + all tests
- `pre-commit` — Lint + type check + changed-file tests
- `pre-pr` — Full suite + coverage report

## Usage

```
/verify quick
/verify pre-pr
```
