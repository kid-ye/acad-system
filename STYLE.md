# Code style

This project follows the [Google style guides](https://github.com/google/styleguide). Adoption is **incremental**: the tooling is configured, but existing code is **not** mass-reformatted. Format and lint files as you touch them, not the whole tree at once.

## Python (backend, scripts)

Follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

- **Lint:** `pylintrc` at the repo root is Google's published rcfile.
- **Format:** [`pyink`](https://github.com/google/pyink), Google's fork of Black, configured in `pyproject.toml` (80-col).

Setup and use:

```bash
pip install -r requirements-dev.txt
pyink backend/app/main.py        # format one file you edited
pylint backend/app/main.py       # lint it
```

## TypeScript / React (frontend)

Formatting follows [`gts`](https://github.com/google/gts) (Google TypeScript Style) via Prettier. The settings in `frontend/.prettierrc.json` match gts: single quotes, no bracket spacing, trailing commas, no-paren single-arg arrows.

```bash
cd frontend
npm run format            # format src/**/*.{ts,tsx,css} you changed
npm run format:check      # check without writing
```

ESLint stays on the existing React/Vite config (`npm run lint`) — it was not swapped for gts's ESLint to avoid churning the working setup. If you later want gts's full ESLint ruleset, that's a separate, larger change.

## Why incremental

Running the formatters across the whole codebase now would produce a large diff touching files unrelated to any real change, making history and review harder. Formatting on edit keeps diffs scoped to actual work and converges the codebase over time.
