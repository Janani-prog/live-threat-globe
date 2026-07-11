# syntax=docker/dockerfile:1

# --- Stage 1: build the frontend -------------------------------------------
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# No VITE_API_BASE_URL / VITE_WS_URL set here on purpose — the frontend
# falls back to relative/derived-from-window.location URLs when unset
# (see frontend/src/lib/apiConfig.ts), which is correct for this
# single-service deployment where the backend serves these same files.
RUN npm run build

# --- Stage 2: backend + built frontend --------------------------------------
FROM python:3.12-slim AS backend
WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend-build /app/frontend/dist ./static

# SQLite lives on whatever persistent/ephemeral disk the host provides
# (see Technical Architecture doc section 4 for the trade-off).
ENV DATABASE_URL=sqlite:///./cyberpulse.db
ENV ENVIRONMENT=production

EXPOSE 8000

# Shell form so ${PORT} expands — hosting providers like Render assign this
# dynamically and won't necessarily use 8000.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
