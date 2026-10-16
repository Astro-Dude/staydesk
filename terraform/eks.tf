################################################################################
# EKS cluster + managed node group + core add-ons
################################################################################

# IAM role for the EBS CSI driver, granted through EKS Pod Identity.
# Without the driver, the in-cluster PostgreSQL PersistentVolumeClaim never binds.
module "ebs_csi_pod_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "2.9.0"

  name = "${var.cluster_name}-ebs-csi"

  attach_aws_ebs_csi_policy = true
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.29.0"

  name               = var.cluster_name
  kubernetes_version = var.kubernetes_version

  # Never fall into EKS extended support (6x the control-plane price);
  # EKS auto-upgrades the control plane when standard support ends instead.
  upgrade_policy = {
    support_type = "STANDARD"
  }

  # Public API endpoint so kubectl / GitHub Actions can reach the cluster.
  endpoint_public_access       = true
  endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs
  endpoint_private_access      = true

  # The identity running `terraform apply` becomes cluster admin.
  enable_cluster_creator_admin_permissions = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cloudwatch_log_group_retention_in_days = 7

  addons = {
    vpc-cni = {
      before_compute = true
    }
    eks-pod-identity-agent = {
      before_compute = true
    }
    kube-proxy = {}
    coredns    = {}
    aws-ebs-csi-driver = {
      pod_identity_association = [{
        role_arn        = module.ebs_csi_pod_identity.iam_role_arn
        service_account = "ebs-csi-controller-sa"
      }]
      # Creates a default gp3 StorageClass so PVCs without a storageClassName bind.
      configuration_values = jsonencode({
        defaultStorageClass = {
          enabled = true
        }
      })
    }
    # Community add-on; provides the Metrics API that the HorizontalPodAutoscaler needs.
    metrics-server = {}
  }

  eks_managed_node_groups = {
    general = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"

      # EKS already launches the newest AMI for the Kubernetes version; skipping the module's
      # SSM lookup means plan doesn't need ssm:GetParameter (denied by some org SCPs).
      use_latest_ami_release_version = false

      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = var.node_disk_size_gb
            volume_type           = "gp3"
            encrypted             = true
            delete_on_termination = true
          }
        }
      }

      labels = {
        workload = "general"
      }
    }
  }

  # Lets the GitHub Actions deploy role (iam-github-oidc.tf) run helm/kubectl.
  access_entries = {
    github_deploy = {
      principal_arn = aws_iam_role.github_deploy.arn

      policy_associations = {
        cluster_admin = {
          policy_arn = "arn:${data.aws_partition.current.partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = {
            type = "cluster"
          }
        }
      }
    }
  }
}
