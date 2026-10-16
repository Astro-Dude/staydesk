#!/usr/bin/env bash
# Generate CPU load on the backend so the HPA scales it out, then watch it happen.
#
# Runs N busybox pods inside the cluster that hammer the backend Service directly (no
# ingress / laptop network in the way).
# Usage: ./scripts/load-test.sh [workers=4] [seconds=180]
#   watch in another terminal:  kubectl get hpa -n staydesk -w
set -euo pipefail
WORKERS="${1:-4}"
DURATION="${2:-180}"
NAMESPACE="${NAMESPACE:-staydesk}"
TARGET="http://staydesk-backend.${NAMESPACE}.svc.cluster.local:8000"

cleanup() { kubectl delete pod -n "$NAMESPACE" -l app=staydesk-load --ignore-not-found --wait=false >/dev/null; }
trap cleanup EXIT

echo "Starting $WORKERS load workers against $TARGET for ${DURATION}s"
for i in $(seq 1 "$WORKERS"); do
  kubectl run "staydesk-load-$i" -n "$NAMESPACE" --image=busybox:1.37 --restart=Never \
    --labels=app=staydesk-load \
    --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":65534,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"load","image":"busybox:1.37","command":["/bin/sh","-c","end=$(( $(date +%s) + '"$DURATION"' )); while [ $(date +%s) -lt $end ]; do wget -q -O /dev/null '"$TARGET"'/api/dashboard/stats; wget -q -O /dev/null '"$TARGET"'/api/reservations; done"],"securityContext":{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}}]}}' \
    >/dev/null
done

end=$(( $(date +%s) + DURATION ))
while [ "$(date +%s)" -lt "$end" ]; do
  status=$(kubectl get hpa staydesk-backend -n "$NAMESPACE" -o jsonpath='cpu {.status.currentMetrics[0].resource.current.averageUtilization}% of request, replicas {.status.currentReplicas} -> {.status.desiredReplicas}' 2>/dev/null || true)
  echo "$(date +%H:%M:%S)  $status"
  sleep 15
done
echo "Load finished; the HPA scales back down after its stabilisation window (~2 min)."
