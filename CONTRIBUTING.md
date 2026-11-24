# Contributing

Thanks for helping. The project is small on purpose.

## Ground rules

- **Standard library only**, Python 3.10+. No runtime dependencies.
- Generated HTML must stay valid and escaped: every config value goes through
  `html.escape` (or `json.dumps` with `<` escaped for JSON-LD).
- Keep the tool generic: no site-specific names, URLs or data in code or tests.

## Setup

```bash
git clone https://github.com/nexina/flutter-web-seo
cd flutter-web-seo
pip install pytest
python -m pytest -q
```

## Making a change

1. Open an issue first for anything bigger than a bug fix.
2. Add or update a test in `tests/` (the end-to-end test in `test_cli.py` is a
   good template).
3. Update `README.md` (config reference) and `CHANGELOG.md` (under "Unreleased").
4. Open a pull request; CI runs the tests on Python 3.10-3.13.
