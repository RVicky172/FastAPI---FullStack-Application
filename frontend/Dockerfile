# ---------------------------------------------------------------------------
# Frontend image: multi-stage build
#   Stage 1 (node):  install deps + `npm run build` -> static files in /app/dist
#   Stage 2 (nginx): serve those static files. Node is NOT in the final image,
#                    so it is small (~50MB instead of ~1GB).
# ---------------------------------------------------------------------------

# ---------- Stage 1: build ----------
FROM node:24-alpine AS build
WORKDIR /app

# Install deps first (cached layer unless package*.json changes)
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite bakes VITE_* variables into the JS bundle AT BUILD TIME.
# The browser (on your machine) calls this URL, so it must be reachable
# from the host - i.e. localhost:8000, not the internal name "backend".
ARG VITE_API_URL=http://localhost:8000/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---------- Stage 2: serve ----------
FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
