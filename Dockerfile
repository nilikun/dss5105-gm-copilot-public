# GM Co-Pilot — one container: FastAPI backend serving the built React app on the same origin.
#   docker build -t gm-copilot .
#   docker run -p 8000:8000 --env-file backend/.env -e ACCESS_CODE=... gm-copilot
# The OpenAI key and access code come from the environment at run time; nothing secret is baked in.

FROM node:24-slim AS web
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY backend/prompts ./prompts
COPY data /app/data
COPY --from=web /src/frontend/dist /app/frontend/dist
RUN useradd --create-home app && mkdir -p var && chown -R app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["/app/backend/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
