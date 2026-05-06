variable "project_name"     { type = string }
variable "environment"      { type = string }
variable "cluster_name"     { type = string }
variable "vpc_id"           { type = string }
variable "private_subnets"  { type = list(string) }
variable "cluster_version"  { type = string }

variable "node_group_config" {
  type = object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size_gb   = number
  })
}
