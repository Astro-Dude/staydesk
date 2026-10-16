variable "aws_region" {
  description = "AWS region for every resource in this stack."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Short project name used for resource names and tags."
  type        = string
  default     = "staydesk"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,20}$", var.project_name))
    error_message = "project_name must be 2-21 lowercase letters, digits or hyphens, starting with a letter."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod). Used in tags."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

################################################################################
# Network
################################################################################

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "Availability zones to spread subnets across. EKS needs at least two."
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "Provide at least two availability zones (EKS requirement)."
  }
}

variable "public_subnet_cidrs" {
  description = "One public subnet CIDR per availability zone (load balancers, NAT gateway)."
  type        = list(string)
  default     = ["10.20.101.0/24", "10.20.102.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == length(var.availability_zones)
    error_message = "Provide exactly one public subnet CIDR per availability zone."
  }
}

variable "private_subnet_cidrs" {
  description = "One private subnet CIDR per availability zone (worker nodes)."
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == length(var.availability_zones)
    error_message = "Provide exactly one private subnet CIDR per availability zone."
  }
}

################################################################################
# EKS
################################################################################

variable "cluster_name" {
  description = "Name of the EKS cluster."
  type        = string
  default     = "staydesk-eks"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version. Pick one in EKS *standard* support (1.34 leaves standard support on 2026-12-02); check with `aws eks describe-cluster-versions`."
  type        = string
  default     = "1.35"

  validation {
    condition     = can(regex("^1\\.[0-9]{2}$", var.kubernetes_version))
    error_message = "kubernetes_version must look like 1.35."
  }
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "CIDRs allowed to reach the public Kubernetes API endpoint. Narrow this to your own IP (x.x.x.x/32) for a real environment."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "node_instance_types" {
  description = "EC2 instance types for the managed node group. c7i-flex.large (2 vCPU / 4 GiB) is Free Tier eligible, which AWS Free-plan accounts require; t3.medium is not."
  type        = list(string)
  default     = ["c7i-flex.large"]
}

variable "node_min_size" {
  description = "Minimum number of worker nodes."
  type        = number
  default     = 1
}

variable "node_desired_size" {
  description = "Desired number of worker nodes."
  type        = number
  default     = 2

  validation {
    condition     = var.node_desired_size >= var.node_min_size && var.node_desired_size <= var.node_max_size
    error_message = "node_desired_size must be between node_min_size and node_max_size."
  }
}

variable "node_max_size" {
  description = "Maximum number of worker nodes."
  type        = number
  default     = 4

  validation {
    condition     = var.node_max_size >= 1 && var.node_max_size <= 10
    error_message = "node_max_size must be between 1 and 10 for this lab."
  }
}

variable "node_disk_size_gb" {
  description = "Root EBS volume size (GiB) for each worker node."
  type        = number
  default     = 30
}

################################################################################
# GitHub Actions deploy access
################################################################################

variable "github_repository" {
  description = "GitHub repository (owner/name) whose main-branch workflows may deploy to the cluster."
  type        = string
  default     = "Astro-Dude/staydesk"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must be in owner/name form."
  }
}

variable "create_github_oidc_provider" {
  description = "Create the GitHub Actions OIDC identity provider. Set to false if your AWS account already has token.actions.githubusercontent.com (only one is allowed per account)."
  type        = bool
  default     = true
}

variable "github_deploy_environment" {
  description = "Optional GitHub Actions environment name (e.g. \"production\"). Set it if the deploy job uses `environment:`, because the OIDC subject then becomes repo:<owner/name>:environment:<name>."
  type        = string
  default     = null
}
