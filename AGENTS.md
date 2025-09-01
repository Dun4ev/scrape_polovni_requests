# Repository Guidelines

## LANGUAGE (Русский по умолчанию)
- Всегда отвечай на р.усском (ru-RU), если явно не указано иное.
- Код (имена переменных/API) — на английском; комментарии и докстринги — на русском.
- Если входной контекст англоязычный, всё равно формируй описание, план, риски и пояснения на русском.
- Если возникает неоднозначность — спроси уточнение, но тоже на русском.
- можешь рассуждать на русском

## Project Structure & Modules
- `app.py`: Streamlit app for interactive analysis and HTML export.
- `src/`: Scrapers and analysis modules (`scrape_polovni_botasaurus.py`, `scrape_mobile_de.py`, `data_loader.py`, `analysis.py`, `econometrics.py`, `plotting.py`).
- `data/`: Working data; `data/raw/*.parquet` are scraped datasets; `data/cars.duckdb` created by the app.
- `results/`, `output/`: Generated reports and artifacts (git‑ignored).
- `error_logs/`, `_debug/`: Logs and debug captures from scrapers.

## Build, Test, and Dev Commands
- Install deps: `pip install -r requirements.txt`
- Run app: `streamlit run app.py`
- Scrape polovni: `python3 src/scrape_polovni_botasaurus.py`
- Scrape mobile.de: `python3 src/scrape_mobile_de.py`
- Lint (optional, local): `ruff check .` or `flake8 .` if you use them.

## Coding Style & Naming
- Follow PEP 8; 4‑space indentation; limit lines to ~100 chars.
- Naming: `snake_case` for files/functions (`data_loader.py`), `PascalCase` for classes, constants `UPPER_SNAKE`.
- Type hints where practical; docstrings for public functions.
- Data files: Parquet in `data/raw/` named by source (e.g., `polovni_automobili.parquet`, `mobile_de.parquet`).

## Testing Guidelines
- No formal test suite yet. Validate changes by:
  - Running scrapers successfully and inspecting new files in `data/raw/`.
  - Launching the app and checking plots, tables, and HTML export.
- If adding tests, prefer `pytest`, place tests under `tests/`, name as `test_*.py`, and use small synthetic DataFrames.

## Commit & Pull Request Guidelines
- Commits: imperative, concise subject; details in body when needed.
  - Example: `Refactor app.py to improve econometric table rendering`.
- PRs: include summary, motivation, key changes, screenshots of UI where relevant, and steps to reproduce (commands and inputs). Link issues and call out any data or schema changes.

## Security & Configuration Tips
- Do not commit secrets or personal data. Scrapers may use proxies; keep credentials in environment variables.
- Large artifacts belong in `results/`/`output/` (already git‑ignored). Be mindful of `data/` size; avoid committing bulky intermediates.
- When editing scrapers, prefer robust selectors and log failures to `error_logs/` for triage.

