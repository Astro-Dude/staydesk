# Submission evidence

This page maps each grading module to where it lives in the repo and the evidence for it.
The screenshots in [`screenshots/`](screenshots) were captured from real runs on
16 Oct 2026. The local Kubernetes evidence comes from the kind cluster that
[`scripts/kind-up.sh`](../scripts/kind-up.sh) builds. The CI/CD and GHCR evidence is the
public GitHub Actions history of this repository.

| Module | Where | Evidence |
|---|---|---|
| **M1** Application | `backend/app/`, `backend/alembic/versions/`, `frontend/src/`, `docker-compose.yml` | [dashboard via Ingress](screenshots/m1-app-dashboard-ingress.png) · [reservations](screenshots/m1-app-reservations.png) · [rooms](screenshots/m1-app-rooms.png) · [mobile](screenshots/m1-app-mobile.png) · [Swagger /docs](screenshots/m1-swagger-docs.png) |
| **M2** Testing | `backend/tests/` (49 tests), `backend/pytest.ini`, `backend/tests/conftest.py` | [pytest -v: 49 passed, 97% coverage](screenshots/m2-pytest-passing.png) |
| **M3** Git & GitHub | this repo, `.gitignore` | commit history on GitHub (≥ 10 descriptive commits) |
| **M4** Docker | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` | [docker compose up --build, non-root uids](screenshots/m4-docker-compose-up.png) · [app served by compose](screenshots/m4-compose-browser-localhost.png) |
| **M5** CI/CD | `.github/workflows/ci-cd.yml` | GitHub → **Actions** (green runs), GitHub → **Packages** (SHA-tagged images) |
| **M6** Trivy | `build-scan-push` job in the workflow | Trivy step log in each Actions run; explanation below |
| **M7** Terraform | `terraform/*.tf`, `terraform/terraform.tfvars.example` | [init / fmt / validate](screenshots/m7-terraform-init-validate.png) |
| **M8** Kubernetes + Helm | `k8s/namespace.yaml`, `helm/staydesk/` | [pods / svc / ingress / helm list](screenshots/m8-kubectl-pods-svc-ingress-helm.png) · [HPA scaled 2 → 6 under load](screenshots/m8-hpa-scaled-to-6.png) · [app through the Ingress host](screenshots/m1-app-dashboard-ingress.png) |
| **M9** Observability | `monitoring/`, chart `servicemonitor.yaml`, `files/grafana-dashboard.json` | [/metrics output](screenshots/m9-metrics-endpoint.png) · [Prometheus targets UP](screenshots/m9-prometheus-targets-up.png) · [Grafana dashboard with live data](screenshots/m9-grafana-dashboard.png) |
| **M10** Docs & demo | [`README.md`](../README.md) (section 12 is the demo script) | live presentation |

Notes on the local captures:

- **Docker Compose.** The compose file publishes 3000 / 8000 / 5432 by default. On the capture
  machine those ports were taken by other local projects, so the run overrode them through
  `.env` variables (`FRONTEND_PORT=3001`, `BACKEND_PORT=18000`, `POSTGRES_PORT=55432`).
- **Kubernetes.** The cluster is kind, a 3-node local cluster. `staydesk.localhost` reaches
  the Traefik ingress controller through kind's port mapping, so no `/etc/hosts` edit is needed.

## M6: what Trivy scanned and what the result means

Trivy scans both images, `staydesk-backend` (Debian 13 slim + Python wheels) and
`staydesk-frontend` (Alpine nginx-unprivileged), after they are built and **before** they are
pushed. It reports OS-package and language-library CVEs and is configured to fail the pipeline
on any HIGH or CRITICAL vulnerability that already has a fix (`ignore-unfixed: true`,
`exit-code: 1`).

A passing scan means that at build time neither image contained a known, fixable HIGH or
CRITICAL CVE. That is partly because the images are kept small: the backend has no pip or
compilers, and the frontend has no Node.js. It does not mean the images are "secure forever":
new CVEs are published daily, so a rebuild of the same Dockerfile can fail later. That is the
point of scanning in every pipeline run.

## M7: AWS evidence

The Terraform passes `init`, `fmt -check` and `validate` (screenshot above), and it is
written to provision the required VPC (2 public + 2 private subnets) and an EKS cluster with
a managed node group. The **`terraform plan`, AWS Console and `terraform destroy`
screenshots** need an AWS account with credentials:

```bash
aws configure                     # or: aws sso login
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform plan  # screenshot 1
terraform apply                   # ~15 min, then screenshot the VPC + EKS console pages
terraform destroy                 # screenshot 2: "Destroy complete!"
```
