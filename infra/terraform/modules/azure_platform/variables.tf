variable "project_name" {
  type        = string
  description = "Short project name used in Azure resource names."
}

variable "environment" {
  type        = string
  description = "Environment name (dev/prod)."
}

variable "location" {
  type        = string
  description = "Azure region."
  default     = "westeurope"
}

variable "aks_node_count" {
  type        = number
  description = "Number of worker nodes in the system pool."
  default     = 2
}

variable "admin_username" {
  type        = string
  description = "Admin username for PostgreSQL Flexible Server."
  default     = "mbcodeadmin"
}

variable "admin_password" {
  type        = string
  description = "Admin password for PostgreSQL Flexible Server."
  sensitive   = true
}

variable "frontdoor_host_name" {
  type        = string
  description = "Public hostname attached to Azure Front Door."
  default     = "mbcode.example.com"
}
