#!/bin/sh
# Container start-up. The first argument picks what to run:
#   all      wait for DB -> migrate -> (optional) seed -> serve   (Docker Compose default)
#   migrate  wait for DB -> migrate -> (optional) seed            (Kubernetes initContainer)
#   serve    start Uvicorn only                                    (Kubernetes main container)
#   *        run any other command, e.g. `sh` or `alembic history`
set -eu

prepare() {
    python -m app.wait_for_db
    alembic upgrade head
    if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
        python -m app.seed
    fi
}

serve() {
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port "${PORT:-8000}" \
        --proxy-headers \
        --forwarded-allow-ips "*"
}

case "${1:-all}" in
    all) prepare; serve ;;
    migrate) prepare ;;
    serve) serve ;;
    *) exec "$@" ;;
esac
