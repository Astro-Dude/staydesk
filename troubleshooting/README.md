# Troubleshooting lab

Three deliberately broken manifests for the live failure demo. Each one is valid YAML and
passes the namespace's `restricted` Pod Security policy, so the problem you see is the one
being taught, not an admission error.

| Lab | Manifest | Symptom | Root cause |
|-----|----------|---------|------------|
| 1 | `broken-image.yaml` | Pod stuck in `ErrImagePull` / `ImagePullBackOff` | Image tag does not exist |
| 2 | `broken-service.yaml` | Service has a ClusterIP but requests time out | Selector matches no pod labels → no endpoints |
| 3 | `broken-readiness.yaml` | Pod `Running` but `0/1 READY`, never restarts | DB unreachable → `/ready` 503 while `/health` 200 |

---

## Lab 1 — ImagePullBackOff

```bash
kubectl apply -f troubleshooting/broken-image.yaml
kubectl get pods -n staydesk -l lab=broken-image          # STATUS: ErrImagePull -> ImagePullBackOff
kubectl describe pod -n staydesk -l lab=broken-image      # Events: "... not found" / "manifest unknown"
kubectl get events -n staydesk --sort-by=.lastTimestamp | tail
```

**Reading the evidence:** `describe` → *Events* shows the kubelet trying to pull
`staydesk-backend:does-not-exist` and the registry answering *not found*. The kubelet backs
off exponentially between retries, hence `BackOff`.

**Fix:** point the Deployment at a tag that exists (CI pushes one per commit SHA):

```bash
kubectl set image deploy/staydesk-broken-image -n staydesk \
  backend=ghcr.io/astro-dude/staydesk-backend:<commit-sha>
# or simply clean up:
kubectl delete -f troubleshooting/broken-image.yaml
```

Other causes of the same symptom: a typo in the registry/repository name, a private GHCR
package without `imagePullSecrets`, or registry rate limits.

## Lab 2 — Service without endpoints

```bash
kubectl apply -f troubleshooting/broken-service.yaml
kubectl get svc -n staydesk staydesk-broken-service                     # has a ClusterIP...
kubectl get endpointslices -n staydesk -l kubernetes.io/service-name=staydesk-broken-service
                                                                        # ...but no endpoints
kubectl describe svc -n staydesk staydesk-broken-service | grep -E 'Selector|Endpoints'
kubectl get pods -n staydesk --show-labels | grep backend               # actual labels
kubectl run curl -n staydesk --rm -it --restart=Never --image=curlimages/curl \
  --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":100,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"curl","image":"curlimages/curl","args":["-sS","--max-time","3","http://staydesk-broken-service:8000/health"],"securityContext":{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}}]}}'
```

**Reading the evidence:** the Service asks for `app.kubernetes.io/component=api`; the pods
carry `app.kubernetes.io/component=backend`. A Service only routes to pods whose labels match
its selector: **no match → no endpoints → no traffic** (connection refused / timeout).

**Fix:**

```bash
kubectl patch svc staydesk-broken-service -n staydesk --type merge \
  -p '{"spec":{"selector":{"app.kubernetes.io/name":"staydesk","app.kubernetes.io/component":"backend"}}}'
kubectl get endpointslices -n staydesk -l kubernetes.io/service-name=staydesk-broken-service   # now lists pod IPs
kubectl delete -f troubleshooting/broken-service.yaml
```

## Lab 3 — Running but not Ready

```bash
kubectl apply -f troubleshooting/broken-readiness.yaml
kubectl get pods -n staydesk -l lab=broken-readiness      # Running, READY 0/1, RESTARTS 0
kubectl describe pod -n staydesk -l lab=broken-readiness  # "Readiness probe failed: HTTP probe failed with statuscode: 503"
kubectl logs -n staydesk -l lab=broken-readiness          # GET /ready 503
kubectl exec -n staydesk deploy/staydesk-broken-readiness -- \
  python -c "import urllib.request as u; print(u.urlopen('http://127.0.0.1:8000/health').read())"
```

**Reading the evidence:** liveness (`/health`) only checks that the process is alive, so it
passes and Kubernetes doesn't restart the container. Readiness (`/ready`) checks the
database; it fails, so the pod is kept **out of the Service's endpoints**: no user traffic
reaches a pod that can't serve it. Restarting wouldn't help, because the database is the
problem, not the process.

**Fix:** correct `DATABASE_URL` (in the real chart it comes from the `staydesk-db` Secret):

```bash
kubectl delete -f troubleshooting/broken-readiness.yaml
```

---

## General triage checklist

```text
kubectl get pods -n staydesk -o wide          what state is it in? which node?
kubectl describe pod <pod> -n staydesk        Events: scheduling, pulling, probes, OOMKilled
kubectl logs <pod> -n staydesk [--previous]   application errors (previous = before restart)
kubectl get events -n staydesk --sort-by=.lastTimestamp
kubectl get svc,endpointslices -n staydesk    is the Service selecting any pods?
kubectl top pods -n staydesk                  CPU / memory (needs metrics-server)
helm history staydesk -n staydesk             what changed? -> helm rollback staydesk <rev>
```
