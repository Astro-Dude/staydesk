#!/usr/bin/env bash
# Build the whole StayDesk platform on a local kind cluster:
#   kind cluster -> Traefik ingress -> metrics-server -> kube-prometheus-stack
#   -> local images -> Helm release of StayDesk.
# Usage: ./scripts/kind-up.sh        (idempotent; re-run to redeploy after code changes)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLUSTER=staydesk
NAMESPACE=staydesk
TRAEFIK_CHART_VERSION=42.0.0
METRICS_SERVER_CHART_VERSION=3.14.0
KPS_CHART_VERSION=92.9.0
TAG="${TAG:-local}"

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

for tool in docker kind kubectl helm; do
  command -v "$tool" >/dev/null || { echo "missing required tool: $tool" >&2; exit 1; }
done

step "kind cluster '$CLUSTER'"
if ! kind get clusters | grep -qx "$CLUSTER"; then
  kind create cluster --config "$ROOT/k8s/kind-config.yaml" --wait 120s
fi
kubectl config use-context "kind-$CLUSTER" >/dev/null

step "Helm repositories"
helm repo add traefik https://traefik.github.io/charts >/dev/null 2>&1 || true
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null 2>&1 || true
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo update traefik metrics-server prometheus-community >/dev/null

step "Ingress controller (Traefik)"
helm upgrade --install traefik traefik/traefik --version "$TRAEFIK_CHART_VERSION" \
  -n traefik --create-namespace -f "$ROOT/k8s/ingress/traefik-values-kind.yaml" --wait

step "metrics-server (Metrics API for the HPA)"
helm upgrade --install metrics-server metrics-server/metrics-server \
  --version "$METRICS_SERVER_CHART_VERSION" -n kube-system \
  -f "$ROOT/k8s/metrics-server-values-kind.yaml" --wait

step "Prometheus + Grafana (kube-prometheus-stack)"
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --version "$KPS_CHART_VERSION" -n monitoring --create-namespace \
  -f "$ROOT/monitoring/kube-prometheus-stack-values.yaml" \
  -f "$ROOT/monitoring/kube-prometheus-stack-values-kind.yaml" --wait --timeout 10m

step "Build images (tag: $TAG) and load them into kind"
docker build -t "staydesk-backend:$TAG" --build-arg GIT_SHA="$TAG" "$ROOT/backend"
docker build -t "staydesk-frontend:$TAG" --build-arg VITE_GIT_SHA="$TAG" "$ROOT/frontend"
kind load docker-image --name "$CLUSTER" "staydesk-backend:$TAG" "staydesk-frontend:$TAG"

step "StayDesk Helm release"
kubectl apply -f "$ROOT/k8s/namespace.yaml"
helm upgrade --install staydesk "$ROOT/helm/staydesk" -n "$NAMESPACE" \
  -f "$ROOT/helm/staydesk/values-dev.yaml" \
  --set backend.image.tag="$TAG" --set frontend.image.tag="$TAG" \
  --wait --timeout 5m

step "Status"
kubectl get pods,svc,ingress,hpa -n "$NAMESPACE"
cat <<MSG

StayDesk  : http://staydesk.localhost        (Swagger: http://staydesk.localhost/docs)
Grafana   : http://grafana.localhost         (user admin, password below)
Prometheus: http://prometheus.localhost/targets

Grafana password:
  kubectl get secret -n monitoring kube-prometheus-stack-grafana -o jsonpath='{.data.admin-password}' | base64 -d; echo
MSG
