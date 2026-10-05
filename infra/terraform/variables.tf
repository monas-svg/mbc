variable "subscription_id" {
  description = "Azure Subscription ID used for provisioning resources."
  type        = string
  default     = ""
}

variable "project_name" {
  description = "Short project name used in Azure resource naming."
  type        = string
  default     = "mbcode"
}

variable "environment" {
  description = "Deployment environment: dev, qa, prod."
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Primary Azure region for the environment."
  type        = string
  default     = "westeurope"
}

variable "aks_node_count" {
  description = "Number of worker nodes for the AKS node pool."
  type        = number
  default     = 2
}

variable "db_admin_login" {
  description = "Admin username for Azure PostgreSQL Flexible Server."
  type        = string
  default     = "mbcodeadmin"
  sensitive   = true
}

variable "db_admin_password" {
  description = "Admin password for Azure PostgreSQL Flexible Server."
  type        = string
  default     = "ChangeMe123!"
  sensitive   = true
}
