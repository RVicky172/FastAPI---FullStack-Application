# ---------------------------------------------------------------------------
# Frontend image, two targets:
#
#   dev  -> Vite dev server with hot module reload (used by docker-compose.yml)
#   prod -> static build served by nginx (used by docker-compose.prod.yml)
#
#   docker build --target dev  ./frontend
#   docker build --target prod ./frontend
# ---------------------------------------------------------------------------

# ---------- base: install dependencies (shared by both targets) ----------
FROM node:24-alpine AS base
WORKDIR /app
RUN chown node:node /app
USER node
# Install deps first (cached layer unless package*.json changes)
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci

# ---------- dev: Vite dev server ----------
FROM base AS dev
COPY --chown=node:node . .
EXPOSE 5173
# --host 0.0.0.0 so the server is reachable from outside the container.
# VITE_API_URL comes from the environment (docker-compose.yml).
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---------- build: compile the production bundle ----------
FROM base AS build
COPY --chown=node:node . .
# Vite bakes VITE_* variables into the JS bundle AT BUILD TIME.
# The browser (on your machine) calls this URL, so it must be reachable
# from the host - i.e. localhost:8000, not the internal name "backend".
ARG VITE_API_URL=http://localhost:8000/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---------- prod: serve static files with nginx (no Node in the final image) ----------
FROM nginx:1.29-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
