output "region" {
  description = "AWS region the stack is deployed in."
  value       = var.aws_region
}

output "vpc_id" {
  description = "ID of the VPC."
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs (internet-facing load balancers, NAT gateway)."
  value       = module.vpc.public_subnets
}

output "private_subnet_ids" {
  description = "Private subnet IDs (EKS worker nodes)."
  value       = module.vpc.private_subnets
}

output "nat_gateway_public_ips" {
  description = "Elastic IPs of the NAT gateway (egress IP of the worker nodes)."
  value       = module.vpc.nat_public_ips
}

output "cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS Kubernetes API endpoint."
  value       = module.eks.cluster_endpoint
}

output "cluster_version" {
  description = "Kubernetes version of the EKS control plane."
  value       = module.eks.cluster_version
}

output "node_group_ids" {
  description = "Managed node group IDs (cluster:nodegroup)."
  value       = [for ng in module.eks.eks_managed_node_groups : ng.node_group_id]
}

output "github_deploy_role_arn" {
  description = "IAM role ARN for GitHub Actions. Save it as the repository variable AWS_DEPLOY_ROLE_ARN."
  value       = aws_iam_role.github_deploy.arn
}

output "github_actions_variables" {
  description = "Repository variables to set in GitHub (Settings -> Secrets and variables -> Actions -> Variables)."
  value = {
    AWS_DEPLOY_ROLE_ARN = aws_iam_role.github_deploy.arn
    AWS_REGION          = var.aws_region
    EKS_CLUSTER_NAME    = module.eks.cluster_name
  }
}

output "configure_kubectl" {
  description = "Command to point kubectl at the new cluster."
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}
