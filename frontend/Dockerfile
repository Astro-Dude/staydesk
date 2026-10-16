# syntax=docker/dockerfile:1

# ---------- Stage 1: build the React app with Node ----------
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
# Commit SHA baked into the bundle and shown in the sidebar ("UI <sha>").
ARG VITE_GIT_SHA=dev
ENV VITE_GIT_SHA=$VITE_GIT_SHA
RUN npm run build

# ---------- Stage 2: serve the static bundle with unprivileged Nginx ----------
FROM nginxinc/nginx-unprivileged:1.30-alpine AS runtime

ARG VITE_GIT_SHA=dev
LABEL org.opencontainers.image.title="staydesk-frontend" \
      org.opencontainers.image.description="StayDesk React frontend served by Nginx" \
      org.opencontainers.image.revision=$VITE_GIT_SHA

# Where /api requests are proxied; overridden per environment (Compose, Helm).
ENV BACKEND_URL=http://backend:8000

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

# nginx-unprivileged already runs as the non-root "nginx" user (uid 101).
USER 101
EXPOSE 8080
