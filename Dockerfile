FROM python:3.14-slim-trixie AS builder

ENV POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1

# Pin poetry to the version that generated poetry.lock (2.3.2) so a future
# poetry major with changed lock semantics cannot break the daily rebuild.
RUN pip install --no-cache-dir poetry==2.3.2

WORKDIR /app

# Metadata first so source changes keep the dependency layer cached.
COPY pyproject.toml poetry.lock README.md ./

# --only main: dev deps (pytest/ruff/mypy/pre-commit) must not leak into the runtime venv.
RUN poetry install --no-root --only main

COPY ozon_schema_fetcher ./ozon_schema_fetcher

# Full install: dependencies (cached) + the project itself into the venv.
RUN poetry install --only main

# Download the Camoufox browser at build time into $HOME/.cache/camoufox.
RUN poetry run python -m camoufox fetch


FROM python:3.14-slim-trixie AS runtime

# Firefox/Camoufox system libraries; trixie renamed packages that moved to a
# 64-bit time_t ABI with a t64 suffix (libasound2t64, libgtk-3-0t64, ...).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fontconfig \
        fonts-liberation \
        libasound2t64 \
        libatk-bridge2.0-0t64 \
        libatk1.0-0t64 \
        libatspi2.0-0t64 \
        libcairo2 \
        libcups2t64 \
        libdbus-glib-1-2 \
        libdrm2 \
        libgbm1 \
        libgtk-3-0t64 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libx11-xcb1 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        libxrender1 \
        libxss1 \
        libxt6t64 \
        libxtst6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Camoufox resolves its browser as expanduser("~")/.cache/camoufox and hangs
# when HOME is missing or unwritable (camoufox #572/#620): run as root with an
# explicit writable HOME (no USER directive, same as the monorepo images; root
# also sidesteps -v mount permission issues for the CI-written schemas/).
ENV HOME=/root \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /root/.cache/camoufox /root/.cache/camoufox
# Keep the package dir so `python -m ozon_schema_fetcher` resolves even if the
# project is installed as editable (a .pth in the venv points back to
# /app/ozon_schema_fetcher).
COPY --from=builder /app/ozon_schema_fetcher /app/ozon_schema_fetcher

ENTRYPOINT ["python", "-m", "ozon_schema_fetcher"]
CMD ["-o", "/schemas/ozon-seller-api-openapi.json"]
