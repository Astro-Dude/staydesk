terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # State is local by default so the lab works with zero setup.
  # For a team / CI setup, copy backend.tf.example to backend.tf and
  # point it at an S3 bucket you own (see README.md).
}
