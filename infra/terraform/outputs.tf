output "resource_group_name" {
  description = "Azure resource group created for the MBCODE platform."
  value       = azurerm_resource_group.this.name
}

output "aks_cluster_name" {
  description = "AKS cluster name."
  value       = azurerm_kubernetes_cluster.this.name
}

output "acr_name" {
  description = "Azure Container Registry name used to host the application image."
  value       = azurerm_container_registry.this.name
}

output "key_vault_name" {
  description = "Key Vault name for app secrets and certificates."
  value       = azurerm_key_vault.this.name
}

output "postgres_server_name" {
  description = "PostgreSQL Flexible Server name."
  value       = azurerm_postgresql_flexible_server.this.name
}

output "postgres_database_name" {
  description = "Database created for the application."
  value       = azurerm_postgresql_flexible_server_database.mbcode.name
}
