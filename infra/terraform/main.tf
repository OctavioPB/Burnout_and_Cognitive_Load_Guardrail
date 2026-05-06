terraform {
  required_version = ">= 1.8.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }

  backend "s3" {
    bucket         = "burnout-guardrail-terraform-state"
    key            = "staging/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "burnout-guardrail-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

module "vpc" {
  source = "./modules/vpc"

  environment          = var.environment
  project_name         = var.project_name
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  private_subnet_cidrs = var.private_subnet_cidrs
  public_subnet_cidrs  = var.public_subnet_cidrs
}

module "eks" {
  source = "./modules/eks"

  environment       = var.environment
  project_name      = var.project_name
  cluster_name      = "${var.project_name}-${var.environment}"
  vpc_id            = module.vpc.vpc_id
  private_subnets   = module.vpc.private_subnet_ids
  cluster_version   = var.eks_cluster_version
  node_group_config = var.node_group_config

  depends_on = [module.vpc]
}

module "kafka" {
  source = "./modules/kafka"

  environment              = var.environment
  project_name             = var.project_name
  cluster_name             = "${var.project_name}-${var.environment}"
  vpc_id                   = module.vpc.vpc_id
  private_subnets          = module.vpc.private_subnet_ids
  kafka_version            = var.kafka_version
  broker_instance_type     = var.kafka_broker_instance_type
  number_of_broker_nodes   = var.kafka_broker_count
  broker_storage_volume_gb = var.kafka_broker_storage_gb

  depends_on = [module.vpc]
}
