################################################################################
# VPC: 2 public + 2 private subnets across two AZs, one shared NAT gateway
################################################################################

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.7.3"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  public_subnets  = var.public_subnet_cidrs
  private_subnets = var.private_subnet_cidrs

  # Private subnets reach the internet (image pulls from GHCR, AWS APIs)
  # through a single NAT gateway. One per AZ is more resilient but costs more.
  enable_nat_gateway     = true
  single_nat_gateway     = true
  one_nat_gateway_per_az = false

  enable_dns_support   = true
  enable_dns_hostnames = true

  # Public subnets host internet-facing load balancers (the ingress controller
  # Service); private subnets host worker nodes and internal load balancers.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}
