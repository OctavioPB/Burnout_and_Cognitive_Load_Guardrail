output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.vpc.public_subnet_ids
}

output "eks_cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "API server endpoint for the EKS cluster"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "eks_cluster_certificate_authority" {
  description = "Base64-encoded CA data for the EKS cluster"
  value       = module.eks.cluster_certificate_authority
  sensitive   = true
}

output "kafka_bootstrap_brokers" {
  description = "TLS bootstrap broker string for MSK cluster"
  value       = module.kafka.bootstrap_brokers_tls
  sensitive   = true
}

output "kafka_zookeeper_connect" {
  description = "Zookeeper connection string for MSK cluster"
  value       = module.kafka.zookeeper_connect_string
  sensitive   = true
}
