variable "project_name" {
  description = "Project name used as a prefix for all resource names"
  type        = string
  default     = "burnout-guardrail"
}

variable "environment" {
  description = "Deployment environment (staging | production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be 'staging' or 'production'."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

# ─── Networking ───────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to deploy into"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# ─── EKS ──────────────────────────────────────────────────────────────────────

variable "eks_cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.30"
}

variable "node_group_config" {
  description = "EKS managed node group configuration"
  type = object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size_gb   = number
  })
  default = {
    instance_types = ["m5.large"]
    min_size       = 2
    max_size       = 6
    desired_size   = 3
    disk_size_gb   = 50
  }
}

# ─── MSK (Managed Kafka) ──────────────────────────────────────────────────────

variable "kafka_version" {
  description = "Apache Kafka version for MSK"
  type        = string
  default     = "3.6.0"
}

variable "kafka_broker_instance_type" {
  description = "EC2 instance type for MSK brokers"
  type        = string
  default     = "kafka.m5.large"
}

variable "kafka_broker_count" {
  description = "Number of MSK broker nodes (must be a multiple of AZ count)"
  type        = number
  default     = 3
}

variable "kafka_broker_storage_gb" {
  description = "EBS storage per broker in GB"
  type        = number
  default     = 100
}
