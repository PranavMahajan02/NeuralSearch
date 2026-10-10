# Public entry point: Caddy serving the built frontend and proxying /api/* to
# the backend. Build context: the repository root.

# ---------------------------------------------------------------------------
FROM node:25-alpine AS frontend

WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
# Same origin: the browser calls https://<host>/api/..., Caddy strips /api.
ENV VITE_API_BASE_URL=/api
RUN npx vite build

# ---------------------------------------------------------------------------
FROM caddy:2.10-alpine

COPY deploy/caddy/Caddyfile /etc/caddy/Caddyfile
COPY --from=frontend /src/dist /srv
