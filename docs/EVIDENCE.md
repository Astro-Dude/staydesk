# Submission evidence

This page maps each grading module to where it lives in the repo and the evidence for it.
The screenshots in [`screenshots/`](screenshots) were captured from real runs on
16 Oct 2026. The local Kubernetes evidence comes from the kind cluster that
[`scripts/kind-up.sh`](../scripts/kind-up.sh) builds. The CI/CD, Trivy and GHCR captures come from
this repository's GitHub Actions run #2 and its GHCR packages.

| Module | Where | Evidence |
|---|---|---|
| **M1** Application | `backend/app/`, `backend/alembic/versions/`, `frontend/src/`, `docker-compose.yml` | [dashboard via Ingress](screenshots/m1-app-dashboard-ingress.png) · [reservations](screenshots/m1-app-reservations.png) · [rooms](screenshots/m1-app-rooms.png) · [mobile](screenshots/m1-app-mobile.png) · [Swagger /docs](screenshots/m1-swagger-docs.png) |
| **M2** Testing | `backend/tests/` (49 tests), `backend/pytest.ini`, `backend/tests/conftest.py` | [pytest -v: 49 passed, 97% coverage](screenshots/m2-pytest-passing.png) |
| **M3** Git & GitHub | this repo, `.gitignore` | [commit history: 18 descriptive commits](screenshots/m3-commit-history.png) · [public repo](screenshots/m3-github-repo.png) |
| **M4** Docker | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` | [docker compose up --build, non-root uids](screenshots/m4-docker-compose-up.png) · [app served by compose](screenshots/m4-compose-browser-localhost.png) |
| **M5** CI/CD | `.github/workflows/ci-cd.yml` | [run #5: every job green, including **Deploy · Helm → EKS**](screenshots/m5-actions-eks-deploy-green.png) · [EKS deploy job (OIDC → kubeconfig → helm)](screenshots/m5-deploy-eks-job.png) · [runs list](screenshots/m5-actions-pipeline-green.png) · [ephemeral kind deploy job](screenshots/m5-deploy-kind-job.png) + [its helm/smoke output](screenshots/m5-deploy-kind-helm-smoke.png) · [GHCR backend, SHA tags](screenshots/m5-ghcr-backend-sha-tags.png) · [GHCR frontend](screenshots/m5-ghcr-frontend-sha-tags.png) · run: https://github.com/Astro-Dude/staydesk/actions/runs/38954572064 |
| **M6** Trivy | `build-scan-push` job in the workflow | [Trivy output from the pipeline: 0 HIGH/CRITICAL in both images](screenshots/m6-trivy-scan-output.png) · [scan step inside the image job](screenshots/m6-trivy-backend-job.png) · explanation below |
| **M7** Terraform | `terraform/*.tf`, `terraform/terraform.tfvars.example` | [init / fmt / validate](screenshots/m7-terraform-init-validate.png) · [`terraform plan`: 61 to add](screenshots/m7-terraform-plan.png) · [`terraform apply` + outputs](screenshots/m7-terraform-apply-and-outputs.png) · AWS Console: [EKS cluster](screenshots/m7-aws-console-eks-cluster.png), [add-ons](screenshots/m7-aws-console-eks-addons.png), [VPC](screenshots/m7-aws-console-vpc.png), [subnets](screenshots/m7-aws-console-subnets.png), [NAT gateway](screenshots/m7-aws-console-nat-gateway.png), [EC2 worker node](screenshots/m7-aws-console-ec2-node.png) · [`terraform destroy`](screenshots/m7-terraform-destroy.png) |
| **M8** Kubernetes + Helm | `k8s/namespace.yaml`, `helm/staydesk/` | **EKS:** [pods / svc / ingress / hpa / pvc / helm list](screenshots/m8-eks-kubectl-pods-svc-ingress-helm.png) · [app via the AWS load balancer](screenshots/m8-eks-app-via-aws-load-balancer.png) · [reservations](screenshots/m8-eks-app-reservations.png) · [Swagger](screenshots/m8-eks-swagger-via-load-balancer.png) · [curl through the LB](screenshots/m8-eks-curl-load-balancer.png) · [HPA 2 → 6 under load](screenshots/m8-eks-hpa-scaled-to-6.png) · [load balancer in the console](screenshots/m8-aws-console-load-balancer.png) · **kind (local):** [pods / svc / ingress / helm](screenshots/m8-kubectl-pods-svc-ingress-helm.png) · [HPA 2 → 6](screenshots/m8-hpa-scaled-to-6.png) |
| **M9** Observability | `monitoring/`, chart `servicemonitor.yaml`, `files/grafana-dashboard.json` | [/metrics output](screenshots/m9-metrics-endpoint.png) · **EKS:** [Prometheus targets UP](screenshots/m9-eks-prometheus-targets-up.png) · [Grafana with live load](screenshots/m9-eks-grafana-dashboard.png) · **kind:** [Prometheus targets](screenshots/m9-prometheus-targets-up.png) · [Grafana](screenshots/m9-grafana-dashboard.png) |
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

## M7 / M8: the AWS run

On 17 Oct 2026 the full lifecycle ran against a real AWS account (`290971955241`, `ap-south-1`):

1. `terraform plan`: 61 to add. `terraform apply` created the VPC (2 public + 2 private
   subnets, one NAT gateway), EKS 1.35, a managed node group, the add-ons (VPC CNI, CoreDNS,
   kube-proxy, Pod Identity, EBS CSI with a default gp3 StorageClass, metrics-server) and the
   GitHub OIDC deploy role.
2. Traefik and kube-prometheus-stack were installed with Helm.
3. A push to `main` ran the pipeline. **Deploy · Helm → EKS** assumed the deploy role through
   GitHub OIDC (no AWS keys stored in GitHub) and ran `helm upgrade --install` with the
   SHA-tagged images. The app answered through the AWS load balancer, `/api/meta` reported
   the deployed commit, the HPA scaled the backend from 2 to 6 pods under load, and
   Prometheus scraped every pod.
4. Helm releases were uninstalled first, which freed the load balancer and the EBS volume.
   Then `terraform destroy` removed every resource, and a final check confirmed no instances,
   load balancers, volumes, NAT gateways or Elastic IPs were left.

Things learned on a brand-new **AWS Free-plan** account (all fixed in the code):

- Only Free-Tier instance types can launch, so the node group uses `c7i-flex.large`
  (2 vCPU / 4 GiB). `t3.medium` is refused.
- New accounts can't create NLB/ALB load balancers until AWS finishes verifying them. A
  Classic Load Balancer still works, so the screenshots show Traefik behind one.
- GitHub's OIDC tokens now carry immutable IDs in `sub`
  (`repo:Astro-Dude@<id>/staydesk@<id>:ref:refs/heads/main`), and the deploy role's trust
  policy accepts both forms.
- To keep cost minimal: one worker node, no customer-managed KMS key, no control-plane log
  shipping, and no persistent volumes for Prometheus or Grafana. The whole run cost about
  US$0.40 of free-plan credits.

The console screenshots come from a temporary **read-only** federated session
(`GetFederationToken` with a Describe/List-only policy), so no password was used and nothing
could be changed from the browser.
