# Terraform — AWS VPC + EKS for StayDesk

This folder provisions the AWS infrastructure StayDesk runs on in production-style mode.
Kubernetes only manages workloads; it cannot create the network or the cluster itself —
that is Terraform's job (Infrastructure as Code: describe the desired state, let Terraform
reconcile it, instead of clicking through the AWS Console).

## What it creates

```text
AWS account (ap-south-1)
│
├── VPC 10.20.0.0/16 ─────────────────────────────── vpc.tf
│   ├── public subnets   10.20.101.0/24 (1a)  10.20.102.0/24 (1b)
│   │     ├── Internet Gateway
│   │     ├── NAT Gateway (single, cost-optimised)
│   │     └── tag kubernetes.io/role/elb=1  → internet-facing LBs (Traefik)
│   └── private subnets  10.20.1.0/24  (1a)   10.20.2.0/24  (1b)
│         └── tag kubernetes.io/role/internal-elb=1
│
├── EKS cluster "staydesk-eks" (Kubernetes 1.35) ─── eks.tf
│   ├── managed node group "general": 2 × t3.medium (min 1 / max 4), AL2023, 30 GiB gp3
│   │     └── runs in the private subnets
│   ├── add-ons: vpc-cni, kube-proxy, coredns, eks-pod-identity-agent,
│   │            aws-ebs-csi-driver (+ default gp3 StorageClass), metrics-server
│   ├── KMS key for Kubernetes secret encryption, CloudWatch control-plane logs (7 days)
│   └── access entries: you (cluster creator) + GitHub deploy role → cluster admin
│
└── IAM ───────────────────────────────────────────── iam-github-oidc.tf
    ├── OIDC provider token.actions.githubusercontent.com
    ├── role staydesk-github-deploy  (trusted only by Astro-Dude/staydesk @ main)
    └── role staydesk-eks-ebs-csi    (EBS CSI driver, via EKS Pod Identity)
```

| File | Purpose |
|------|---------|
| `versions.tf` | Terraform + AWS provider version constraints |
| `providers.tf` | AWS provider, region, default tags on every resource |
| `variables.tf` | All inputs, with descriptions and validation |
| `vpc.tf` | VPC, subnets, NAT gateway (`terraform-aws-modules/vpc/aws` 6.7.3) |
| `eks.tf` | EKS cluster, node group, add-ons (`terraform-aws-modules/eks/aws` 21.29.0) |
| `iam-github-oidc.tf` | Keyless GitHub Actions → AWS access for the deploy job |
| `outputs.tf` | Cluster name/endpoint, subnet IDs, deploy role ARN, kubectl command |
| `terraform.tfvars.example` | Example inputs — copy to `terraform.tfvars` (gitignored) |
| `backend.tf.example` | Optional S3 remote state |
| `.terraform.lock.hcl` | Provider checksums — committed so every machine uses the same provider build |

## Prerequisites

- Terraform >= 1.9 (`terraform version`)
- AWS CLI v2 with credentials for an account you can create IAM/EKS/VPC resources in:
  `aws configure` (access key) or `aws configure sso && aws sso login`.
  Check with `aws sts get-caller-identity`.
- `kubectl` and `helm` for the steps after the cluster exists.

> **Never commit credentials.** AWS keys live in `~/.aws/`, not in this repo.
> `terraform.tfvars` and all `*.tfstate` files are gitignored because state can contain secrets.

## Run it

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # optional: adjust values

terraform init          # downloads the AWS provider and modules
terraform fmt -recursive
terraform validate
terraform plan -out tfplan    # ~60 resources to add
terraform apply tfplan        # ~15-20 minutes (EKS control plane is the slow part)
```

Point kubectl at the cluster (the exact command is also an output):

```bash
$(terraform output -raw configure_kubectl)
kubectl get nodes                 # 2 nodes, STATUS Ready
kubectl get storageclass          # ebs-csi-default-sc (default)
kubectl top nodes                 # works once metrics-server is up → HPA will work
```

### Connect GitHub Actions (deploy job)

The pipeline authenticates to AWS with OIDC — no AWS keys are stored in GitHub.
After `apply`, copy the values into the repository:
**Settings → Secrets and variables → Actions → Variables → New repository variable**

```bash
terraform output github_actions_variables
```

| Repository variable | Value |
|---------------------|-------|
| `AWS_DEPLOY_ROLE_ARN` | `terraform output -raw github_deploy_role_arn` |
| `AWS_REGION` | `ap-south-1` |
| `EKS_CLUSTER_NAME` | `staydesk-eks` |

The role trusts only `repo:Astro-Dude/staydesk:ref:refs/heads/main`. If you fork/rename the
repository, set `github_repository` in `terraform.tfvars`. If the deploy job uses a GitHub
`environment:`, set `github_deploy_environment` too (the OIDC subject changes).

## Cost — read this

Approximate on-demand prices in ap-south-1 (check the AWS pricing pages for current numbers):

| Resource | Approx. cost |
|----------|--------------|
| EKS control plane (standard support) | $0.10 / hour |
| 2 × t3.medium worker nodes | ~$0.045 / hour each |
| NAT gateway | ~$0.056 / hour + per-GB data processed |
| Load balancer created by the ingress controller | ~$0.025 / hour + LCU |
| EBS: 2 × 30 GiB node disks + PostgreSQL PVC (gp3) | a few $ / month |
| KMS key, CloudWatch logs | ~$1 / month + ingestion |

**Roughly $0.30/hour ≈ $7/day while it is running.** Leaving it up for a month costs
well over $200.

`upgrade_policy.support_type = "STANDARD"` stops the cluster from silently moving into
EKS *extended* support (6× the control-plane price) — EKS auto-upgrades the version instead.
That is also why the default version is 1.35: 1.34 leaves standard support on 2026-12-02.

## Destroy when you are done

> ⚠️ **Run `terraform destroy` after the evaluation. Runaway AWS bills are your responsibility.**

Kubernetes creates some AWS resources that Terraform does not know about: the load balancer
behind the ingress controller's `LoadBalancer` Service and the EBS volume behind the
PostgreSQL PVC. Remove them **first**, otherwise the VPC cannot be deleted:

```bash
helm uninstall staydesk -n staydesk                 # app (PVC → EBS volume deleted)
kubectl delete pvc --all -n staydesk                # in case any PVC is left over
helm uninstall kube-prometheus-stack -n monitoring  # if installed
helm uninstall traefik -n traefik                   # deletes the AWS load balancer
kubectl get svc -A | grep LoadBalancer              # must print nothing

terraform destroy                                   # ~10-15 minutes
```

Confirm in the AWS Console (region ap-south-1) that EKS → Clusters, VPC → Your VPCs
(staydesk-vpc), EC2 → Load Balancers and EC2 → Volumes are all empty.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `destroy` hangs on subnets / IGW / VPC (`DependencyViolation`) | A load balancer or ENI created by Kubernetes is still in the VPC. Uninstall the Traefik release (or delete the LB in EC2 → Load Balancers), wait a minute, re-run `terraform destroy`. |
| `EntityAlreadyExists` for the OIDC provider | The account already has the GitHub OIDC provider. Set `create_github_oidc_provider = false`. |
| `UnsupportedAvailabilityZoneException` | Pick different AZs in `availability_zones`. |
| `kubectl` → `You must be logged in to the server (Unauthorized)` | You are using a different AWS identity than the one that ran `apply`. Use the same profile, or add an access entry for your role. |
| PostgreSQL pod `Pending`, PVC `Pending` | `kubectl get storageclass` must show a default class; check `kubectl -n kube-system get pods -l app.kubernetes.io/name=aws-ebs-csi-driver`. |
| HPA shows `<unknown>/60%` | metrics-server not ready yet: `kubectl -n kube-system get deploy metrics-server`. |
| Unsupported Kubernetes version | `aws eks describe-cluster-versions --region ap-south-1` and set `kubernetes_version`. |

## Hardening ideas (beyond the capstone)

- Restrict `cluster_endpoint_public_access_cidrs` to your own IP.
- Scope the GitHub deploy role to the `staydesk` namespace
  (`access_scope = { type = "namespace", namespaces = ["staydesk"] }` with
  `AmazonEKSAdminPolicy`) instead of cluster admin.
- One NAT gateway per AZ (`single_nat_gateway = false`) for resilience.
- Remote state in S3 with locking (`backend.tf.example`).
- Amazon RDS for PostgreSQL instead of an in-cluster database.
