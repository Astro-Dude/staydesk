################################################################################
# GitHub Actions -> AWS via OIDC (no long-lived AWS keys stored in GitHub)
################################################################################

data "aws_partition" "current" {}

resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_github_oidc_provider ? 1 : 0

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

# Reuse the provider if the account already has one (only one is allowed per URL).
data "aws_iam_openid_connect_provider" "github" {
  count = var.create_github_oidc_provider ? 0 : 1

  url = "https://token.actions.githubusercontent.com"
}

locals {
  github_oidc_provider_arn = (
    var.create_github_oidc_provider
    ? aws_iam_openid_connect_provider.github[0].arn
    : data.aws_iam_openid_connect_provider.github[0].arn
  )

  # Only workflows running on the main branch of this repository may assume the role.
  github_oidc_subjects = concat(
    ["repo:${var.github_repository}:ref:refs/heads/main"],
    var.github_deploy_environment == null ? [] : ["repo:${var.github_repository}:environment:${var.github_deploy_environment}"],
  )
}

data "aws_iam_policy_document" "github_deploy_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.github_oidc_subjects
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name                 = "${var.project_name}-github-deploy"
  description          = "Assumed by GitHub Actions (${var.github_repository}) to deploy StayDesk to EKS with Helm."
  assume_role_policy   = data.aws_iam_policy_document.github_deploy_assume.json
  max_session_duration = 3600
}

# Just enough AWS permission for `aws eks update-kubeconfig`.
# Kubernetes permissions come from the EKS access entry in eks.tf.
data "aws_iam_policy_document" "github_deploy_eks" {
  statement {
    effect    = "Allow"
    actions   = ["eks:DescribeCluster"]
    resources = [module.eks.cluster_arn]
  }
}

resource "aws_iam_role_policy" "github_deploy_eks" {
  name   = "eks-describe-cluster"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy_eks.json
}
