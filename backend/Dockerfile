# syntax=docker/dockerfile:1

# ---------- build stage: resolve dependencies into an isolated virtualenv ----------
FROM python:3.13-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    # pip isn't needed at runtime; dropping it shrinks the image and the CVE surface.
    && pip uninstall -y pip

# ---------- runtime stage: only the venv and application code ----------
FROM python:3.13-slim AS runtime
ARG GIT_SHA=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    GIT_SHA=${GIT_SHA}
LABEL org.opencontainers.image.title="staydesk-backend" \
      org.opencontainers.image.description="StayDesk FastAPI backend" \
      org.opencontainers.image.revision="${GIT_SHA}"

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
    && python -m pip uninstall -y pip

WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY --chmod=0755 docker-entrypoint.sh ./

# Numeric UID so Kubernetes `runAsNonRoot` can verify it without resolving names.
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["all"]
