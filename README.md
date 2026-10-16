# StayDesk: hotel front-office platform

StayDesk is a small hotel management app for the front desk. Staff can see occupancy at a glance,
take bookings without double-booking a room, check guests in and out, and keep housekeeping in
step: a room becomes *needs cleaning* after check-out and can't take a new guest until it is
marked clean.

This repo is my **DevOps final capstone (Session 21)**. The point is not only the app. It is the
path the app takes from a laptop to a monitored, autoscaled Kubernetes deployment:

```text
Developer ─▶ GitHub ─▶ GitHub Actions ─────────────────────────────────────────┐
                        ├─ ruff + pytest (49 tests, coverage gate)             │
                        ├─ frontend build                                      │
                        ├─ docker build  (tag = commit SHA)                    │
                        ├─ Trivy scan    (fails on fixable HIGH/CRITICAL)      │
                        └─ push to GHCR ─▶ helm upgrade --install (OIDC → EKS) │
                                                                               ▼
   Terraform ─▶ AWS: VPC (2 public + 2 private subnets, NAT) ─▶ EKS 1.35 + managed node group
                                                                               │
                         Traefik Ingress ◀── staydesk.<host>  ─────────────────┘
                          │  /        → frontend Service → React SPA (nginx, 2 pods)
                          │  /api     → backend  Service → FastAPI (2–6 pods, HPA on CPU)
                          │  /docs                              │
                          │                                     ▼
                          │                         PostgreSQL StatefulSet + PVC (EBS gp3)
                          ▼
              Prometheus (ServiceMonitor scrapes /metrics) ─▶ Grafana "StayDesk · API overview"
```

| Layer | Tech |
|---|---|
| Frontend | React 19 + Vite, hand-written responsive CSS, served by `nginx-unprivileged` |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, Uvicorn |
| Database | PostgreSQL 17 |
| Tests | pytest + coverage, ruff (lint + format) |
| Containers | Multi-stage Dockerfiles, non-root users, Docker Compose |
| CI/CD | GitHub Actions → Trivy → GitHub Container Registry → Helm deploy |
| Infrastructure | Terraform: AWS VPC + EKS (+ EBS CSI, metrics-server, GitHub OIDC role) |
| Kubernetes | Helm chart, Traefik Ingress, HPA, PDBs, NetworkPolicy, restricted Pod Security |
| Observability | kube-prometheus-stack: Prometheus Operator, Prometheus, Grafana |

> **Evidence for each grading module** (screenshots of tests, compose, Kubernetes, HPA,
> Prometheus and Grafana) is indexed in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

---

## Contents

1. [What the app does](#1-what-the-app-does)
2. [Repository layout](#2-repository-layout)
3. [Run it locally with Docker Compose](#3-run-it-locally-with-docker-compose)
4. [REST API](#4-rest-api)
5. [Tests](#5-tests)
6. [CI/CD pipeline](#6-cicd-pipeline)
7. [Security scanning (Trivy)](#7-security-scanning-trivy)
8. [Terraform: AWS VPC + EKS](#8-terraform-aws-vpc--eks)
9. [Kubernetes + Helm](#9-kubernetes--helm)
10. [Ingress, autoscaling and monitoring](#10-ingress-autoscaling-and-monitoring)
11. [Troubleshooting lab](#11-troubleshooting-lab)
12. [Live demo script](#12-live-demo-script)
13. [Clean-up and cost](#13-clean-up-and-cost)

---

## 1. What the app does

| Screen | What you can do |
|---|---|
| **Dashboard** | Occupancy %, arrivals and departures today, in-house guests, booked revenue this month; a *Today at the front desk* worklist with one-click **Check in / Check out**; a live colour-coded room grid; upcoming stays |
| **Rooms** | Every room as a card (type, floor, capacity, ₹ rate, state). Mark clean / dirty, take a room out of service, add or delete rooms |
| **Reservations** | All bookings with status tabs and search. **New reservation** only offers rooms that are actually free for the chosen dates and party size, and shows the price as you type |

Business rules enforced by the API (and covered by tests):

- A room can't be booked twice for overlapping nights. The check-out day is free for the next
  guest, so back-to-back bookings are allowed.
- Bookings can't start in the past, exceed the room's capacity, or run longer than 30 nights.
- Status flow: `BOOKED → CHECKED_IN → CHECKED_OUT`, or `BOOKED → CANCELLED`. Anything else is a `409`.
- Check-in only happens during the stay window, and only into a **clean** room that nobody else occupies.
- Check-out marks the room **dirty**; out-of-service rooms can't be booked.
- The price is fixed at booking time (`nights × nightly rate`), so changing a rate later doesn't
  rewrite existing bookings.

The sidebar footer shows `UI <sha> · API <sha>`, the commit each running container was
built from. During the live demo this is how you see a new deployment arrive.

## 2. Repository layout

```text
.
├── backend/                  FastAPI service
│   ├── app/                  config, models, schemas, routers, metrics, seed data
│   ├── alembic/versions/     0001_create_rooms, 0002_create_reservations
│   ├── tests/                pytest suite (SQLite in memory, never the real DB)
│   ├── Dockerfile            multi-stage, non-root (uid 10001)
│   └── docker-entrypoint.sh  wait for DB → migrate → seed → serve
├── frontend/                 React + Vite SPA
│   ├── src/                  App, components, API client, styles
│   ├── nginx/                nginx config template (BACKEND_URL substituted at start)
│   └── Dockerfile            multi-stage: node build → nginx-unprivileged (uid 101)
├── docker-compose.yml        postgres + backend + frontend
├── .github/workflows/        ci-cd.yml: test → build → scan → push → deploy
├── terraform/                AWS VPC + EKS + add-ons + GitHub OIDC deploy role
├── helm/staydesk/            Helm chart (values.yaml, values-dev.yaml, values-prod.yaml)
├── k8s/                      namespace, kind cluster config, ingress-controller values
├── monitoring/               kube-prometheus-stack values (Prometheus + Grafana)
├── scripts/                  kind-up / kind-down, smoke test, load test
└── troubleshooting/          broken manifests + investigation guide
```

## 3. Run it locally with Docker Compose

Requirements: Docker Desktop (or Docker Engine + Compose v2).

```bash
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:3000 | StayDesk UI |
| http://localhost:8000/docs | Swagger UI (try every endpoint) |
| http://localhost:8000/health · `/ready` · `/metrics` | Probes and Prometheus metrics |

On first start the backend waits for PostgreSQL, runs the Alembic migrations, and loads
**demo data**: 12 rooms and 10 reservations dated relative to today, so the dashboard is never
empty. If ports 3000/8000/5432 are taken, copy `.env.example` to `.env` and change them.

```bash
docker compose exec postgres psql -U staydesk -d staydesk -c "select * from rooms;"   # the tables
docker compose down        # stop
docker compose down -v     # stop and delete the database volume
```

<details>
<summary>Run the backend without Docker</summary>

```bash
cd backend
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL='postgresql+psycopg://staydesk:staydesk@localhost:5432/staydesk'
alembic upgrade head
python -m app.seed                 # optional demo data
uvicorn app.main:app --reload --port 8000
```

Frontend dev server (proxies `/api` to `localhost:8000`):

```bash
cd frontend && npm ci && npm run dev     # http://localhost:5173
```
</details>

## 4. REST API

Interactive docs: `/docs`. All JSON. Errors look like `{"detail": "..."}`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness: the process is up (never touches the DB) |
| GET | `/ready` | Readiness: DB reachable and migrated (`503` otherwise) |
| GET | `/metrics` | Prometheus metrics (HTTP + business counters) |
| GET | `/api/meta` | Service version and the git SHA of the running build |
| GET | `/api/rooms` | List rooms (`?room_type=`, `?housekeeping=`) |
| GET | `/api/rooms/availability` | Rooms free for `?check_in=&check_out=&guests=` |
| GET | `/api/rooms/{id}` | One room |
| POST | `/api/rooms` | Create a room (`409` duplicate number) |
| PUT | `/api/rooms/{id}` | Update a room (rate, housekeeping state, …) |
| DELETE | `/api/rooms/{id}` | Delete a room (`409` if it has upcoming/in-house stays) |
| GET | `/api/reservations` | List reservations (`?status=`, `?room_id=`) |
| GET | `/api/reservations/{id}` | One reservation |
| POST | `/api/reservations` | Book a stay (`409` overlap, `422` bad dates/capacity) |
| PUT | `/api/reservations/{id}` | Change a booked stay (re-validated and re-priced) |
| DELETE | `/api/reservations/{id}` | Delete (`409` while the guest is checked in) |
| POST | `/api/reservations/{id}/check-in` | Check in |
| POST | `/api/reservations/{id}/check-out` | Check out (room → dirty) |
| POST | `/api/reservations/{id}/cancel` | Cancel a booked stay |
| GET | `/api/dashboard/stats` | Occupancy, arrivals, departures, revenue |
| GET | `/api/dashboard/today` | Today's arrivals and departures |

## 5. Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v                       # 49 tests
pytest --cov                    # ~97% line coverage
ruff check . && ruff format --check .
```

- `tests/conftest.py` gives **every test its own in-memory SQLite database** through FastAPI
  dependency overrides, plus a pinned "today", so the date rules are deterministic. The real
  PostgreSQL is never touched.
- The tests cover probes and metrics, room CRUD and availability, every reservation rule and
  status transition, dashboard maths, the seed data, and a test that runs the **Alembic
  migrations** up and down. That last one proves the migrations match the models.
- In CI, a failing test fails the job, and nothing after it runs: **bad code never becomes an image.**

## 6. CI/CD pipeline

`.github/workflows/ci-cd.yml` runs on every push to `main`, on pull requests and on manual dispatch.

```text
┌─ backend-test ── ruff, pytest -v, coverage ≥ 85% ─┐                                                ┌▶ deploy-kind  helm → ephemeral kind + smoke test
├─ frontend-build ─ npm ci, vite build ─────────────┼─▶ build-scan-push (matrix: backend, frontend) ─┤
└─ iac-scan ─────── Trivy config scan (report) ─────┘     docker build → Trivy → push to GHCR         └▶ deploy       helm → EKS (when AWS is configured)
```

- **Image tags are the commit SHA**: `ghcr.io/astro-dude/staydesk-backend:<sha>`. There is no
  `latest`, so every running pod traces back to one commit (commit A → image A).
- Pull requests build and scan but **never push or deploy**.
- Every third-party action is **pinned to a full commit SHA**. Tags are mutable: in March 2026
  attackers force-pushed 76 of 77 `aquasecurity/trivy-action` tags to credential-stealing code,
  and SHA pinning is the defence.
- **Deploy · Helm → kind (ephemeral)** runs on every push to `main`. It creates a throwaway
  3-node kind cluster on the runner with Traefik, pulls the images this run just pushed to
  GHCR, runs `helm upgrade --install --wait --rollback-on-failure`, then smoke-tests every
  route through the Ingress. It also checks that `/api/meta` reports the commit being
  deployed, so each push proves the chart really deploys that exact build.
- **Deploy · Helm → EKS** uses GitHub OIDC to assume an AWS role created by Terraform, so no AWS keys are
  stored in GitHub. It runs `helm upgrade --install … --rollback-on-failure`, then verifies the
  rollout. The job is skipped until the repository variable `AWS_DEPLOY_ROLE_ARN` is set, so
  the pipeline stays green before the AWS infrastructure exists.

## 7. Security scanning (Trivy)

Each image is scanned **before** it is pushed: OS packages (Debian / Alpine) and language
libraries (Python wheels, and npm packages in the frontend build). The job fails if Trivy finds
a **HIGH or CRITICAL CVE that already has a fixed version** (`ignore-unfixed: true`, `exit-code: 1`).
CVEs without a fix are reported, but there is nothing to upgrade to yet.

A clean scan means no known, fixable HIGH/CRITICAL vulnerability was in the image at build
time. It is not a guarantee of security: new CVEs are published daily, so the same image
can fail tomorrow. Image scanning is one layer, next to:

| Layer | Here |
|---|---|
| Dependency pinning | exact versions in `requirements.txt`, `package-lock.json`, `.terraform.lock.hcl` |
| Container scanning | Trivy image scan, blocking |
| IaC misconfiguration | Trivy config scan of Terraform, Helm and Dockerfiles (report-only) |
| Secret hygiene | `.gitignore` for `.env`/`*.tfvars`/state, OIDC instead of AWS keys, random DB password in a Kubernetes Secret |
| Runtime hardening | non-root containers, read-only root filesystems, all capabilities dropped, `restricted` Pod Security, NetworkPolicy around PostgreSQL |

Reducing the attack surface also helps the scan: the backend runtime image has no `pip` and no
build tools, and the frontend runtime is a 26 MB nginx image with no Node.js in it.

## 8. Terraform: AWS VPC + EKS

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # gitignored; never put keys in it
terraform init
terraform plan
terraform apply                                # ~15 min
aws eks update-kubeconfig --region ap-south-1 --name staydesk-eks
```

It creates, in `ap-south-1`:

- a **VPC** `10.20.0.0/16` with **2 public + 2 private subnets** across two AZs, one NAT
  gateway, and the subnet tags Kubernetes load balancers need
- an **EKS 1.35** cluster (standard support only, so no extended-support pricing) with a
  **managed node group** of `t3.medium` nodes (min 1, desired 2, max 4) in the private subnets
- add-ons: VPC CNI, CoreDNS, kube-proxy, Pod Identity agent, **EBS CSI driver** (default
  gp3 StorageClass for the PostgreSQL volume), and **metrics-server** for the HPA
- a **GitHub OIDC deploy role** that only `Astro-Dude/staydesk` on `main` can assume

`terraform output github_actions_variables` prints the three repository variables the deploy
job needs (`AWS_DEPLOY_ROLE_ARN`, `AWS_REGION`, `EKS_CLUSTER_NAME`). See
[`terraform/README.md`](terraform/README.md) for details and the cost table.

## 9. Kubernetes + Helm

The chart in `helm/staydesk` packages the whole app:

| Resource | Notes |
|---|---|
| `Deployment` backend | 2+ replicas; an init container runs migrations (advisory-locked) and seeds; startup, liveness (`/health`) and readiness (`/ready`) probes |
| `Deployment` frontend | 2 replicas, nginx on 8080, read-only root filesystem |
| `Service` ×3 | ClusterIP for backend and frontend; headless for PostgreSQL |
| `StatefulSet` postgres | PostgreSQL 17 + PersistentVolumeClaim (`volumeClaimTemplates`) |
| `Secret` | `DATABASE_URL` and a random password generated once and kept across upgrades |
| `Ingress` | `/` → frontend, `/api` `/docs` `/openapi.json` → backend |
| `HorizontalPodAutoscaler` | backend 2–6 pods at 60% CPU of the request |
| `PodDisruptionBudget` ×2 | at least one pod of each tier survives node drains |
| `NetworkPolicy` | only backend pods may reach PostgreSQL |
| `ServiceMonitor` + dashboard `ConfigMap` | Prometheus scraping and a provisioned Grafana dashboard |

### Local: the full stack on kind (one command)

```bash
./scripts/kind-up.sh
```

This creates a 3-node kind cluster and installs Traefik, metrics-server and
kube-prometheus-stack. It then builds both images, loads them into the cluster, and runs
`helm upgrade --install staydesk`.

| URL | What |
|---|---|
| http://staydesk.localhost | the app **through the Ingress** (`*.localhost` resolves to 127.0.0.1, no `/etc/hosts` edit) |
| http://staydesk.localhost/docs | Swagger through the Ingress |
| http://grafana.localhost | Grafana → *StayDesk → StayDesk · API overview* |
| http://prometheus.localhost/targets | Prometheus targets (`staydesk-backend` should be **UP**) |

```bash
kubectl get pods -n staydesk          # all Running
kubectl get svc -n staydesk
helm list -n staydesk
./scripts/smoke-test.sh               # checks the main routes through the Ingress
```

### AWS EKS

After `terraform apply`:

```bash
aws eks update-kubeconfig --region ap-south-1 --name staydesk-eks
helm repo add traefik https://traefik.github.io/charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install traefik traefik/traefik --version 42.0.0 -n traefik --create-namespace \
  -f k8s/ingress/traefik-values-eks.yaml
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --version 92.9.0 -n monitoring --create-namespace -f monitoring/kube-prometheus-stack-values.yaml
kubectl apply -f k8s/namespace.yaml
helm upgrade --install staydesk ./helm/staydesk -n staydesk -f helm/staydesk/values-prod.yaml \
  --set backend.image.tag=<commit-sha> --set frontend.image.tag=<commit-sha>
kubectl get svc -n traefik traefik    # EXTERNAL-IP = public NLB hostname → open it in a browser
```

After the first manual install, every push to `main` redeploys through the pipeline. GHCR
packages start out **private**. Either make `staydesk-backend` and `staydesk-frontend` public
(*GitHub → Packages → Package settings → Change visibility*), or create a pull secret and set
`imagePullSecrets`.

> **Why Traefik and not ingress-nginx?** The community `ingress-nginx` controller was retired
> in March 2026 and no longer receives security fixes. The chart uses a standard
> `networking.k8s.io/v1` **Ingress**. That resource is only configuration; Traefik is the
> controller that implements it. Swapping controllers is one value: `ingress.className`.

## 10. Ingress, autoscaling and monitoring

**Ingress.** One host, two backends. `/` goes to the React frontend Service and `/api` goes
straight to the FastAPI Service. The browser only ever calls relative `/api/...` URLs, so it
never needs to know an internal hostname.

**HPA.** It scales the backend between 2 and 6 pods on CPU utilisation, measured against the
container's CPU *request*. That is why requests are always set: no request, no scaling. To demo it:

```bash
kubectl get hpa -n staydesk -w        # terminal 1
./scripts/load-test.sh 4 180          # terminal 2: 4 in-cluster workers for 3 minutes
```

Replicas climb as CPU passes the target. After the load stops they fall back to 2 once the
2-minute scale-down stabilisation window has passed.

**Prometheus.** The backend exposes `/metrics` through `prometheus-fastapi-instrumentator`
(request counts, latency histograms per endpoint) plus a business counter,
`staydesk_reservation_events_total{event="created|checked_in|checked_out|cancelled"}`. The
chart's **ServiceMonitor** tells the Prometheus Operator to scrape it every 15 s.

**Grafana.** The dashboard *StayDesk · API overview* is provisioned automatically from a
ConfigMap. It shows request rate, p95 latency, 5xx error rate, responses by status class,
reservation events, CPU per pod against its request, and HPA current/desired replicas.

## 11. Troubleshooting lab

[`troubleshooting/`](troubleshooting/README.md) has three deliberately broken manifests,
each with the commands to investigate and fix it:

| Lab | Symptom | Lesson |
|---|---|---|
| `broken-image.yaml` | `ImagePullBackOff` | `describe pod` → Events → wrong tag |
| `broken-service.yaml` | Service with no endpoints | Services select pods **by label** |
| `broken-readiness.yaml` | `Running` but `0/1 Ready` | liveness vs readiness |

## 12. Live demo script

1. **App**: open http://staydesk.localhost, book a stay, check a guest in.
2. **API**: `/docs`, then create, read, update and delete a room.
3. **Database**: `kubectl exec -n staydesk staydesk-postgres-0 -- psql -U staydesk -d staydesk -c 'select * from reservations;'`
4. **Git**: change something visible (e.g. the dashboard greeting), `git commit`, `git push`.
5. **CI**: GitHub → Actions. Tests run, then images build.
6. **Docker / Trivy / GHCR**: the scan output in the job log, then the new SHA-tagged images under *Packages*.
7. **Terraform**: walk through `terraform/vpc.tf` and `eks.tf`; `terraform plan`.
8. **Kubernetes / Helm**: `kubectl get pods,svc -n staydesk`, `helm list -n staydesk`, `helm history staydesk -n staydesk`.
9. **Ingress**: the app on its hostname; `kubectl get ingress -n staydesk`.
10. **HPA**: `./scripts/load-test.sh` while watching `kubectl get hpa -n staydesk -w`.
11. **Monitoring**: Prometheus targets **UP**, Grafana dashboard reacting to the load.
12. **Failure**: `kubectl apply -f troubleshooting/broken-service.yaml`, diagnose it, fix it.
13. **Rollout**: the sidebar's `UI/API <sha>` now shows the commit from step 4.

## 13. Clean-up and cost

```bash
./scripts/kind-down.sh                                   # local cluster
helm uninstall staydesk -n staydesk                      # on EKS: remove the app (and its PVC)
helm uninstall traefik -n traefik                        # delete the NLB *before* destroying the VPC
helm uninstall kube-prometheus-stack -n monitoring
cd terraform && terraform destroy
```

An EKS control plane, two `t3.medium` nodes and a NAT gateway cost roughly **US$0.25–0.30 per
hour** in `ap-south-1`. Run `terraform destroy` as soon as the evaluation is done.
