data "azurerm_client_config" "current" {}

locals {
  resource_suffix = lower(replace("${var.project_name}${var.environment}", "-", ""))
  acr_name        = substr(lower(replace("${var.project_name}${var.environment}acr", "-", "")), 0, 50)
  kv_name         = substr(lower(replace("${var.project_name}${var.environment}kv", "-", "")), 0, 24)
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.resource_suffix}"
  location = var.location
  tags = {
    environment = var.environment
    managed_by  = "terraform"
    app         = var.project_name
  }
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = "law-${local.resource_suffix}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_registry" "this" {
  name                          = local.acr_name
  resource_group_name           = azurerm_resource_group.this.name
  location                      = azurerm_resource_group.this.location
  sku                           = "Standard"
  admin_enabled                 = false
  public_network_access_enabled = true

  tags = {
    environment = var.environment
    app         = var.project_name
  }
}

resource "azurerm_key_vault" "this" {
  name                          = local.kv_name
  location                      = azurerm_resource_group.this.location
  resource_group_name           = azurerm_resource_group.this.name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  enable_rbac_authorization     = true
  soft_delete_retention_days    = 90
  purge_protection_enabled      = true
  public_network_access_enabled = true

  tags = {
    environment = var.environment
    app         = var.project_name
  }
}

resource "azurerm_user_assigned_identity" "aks" {
  name                = "id-aks-${local.resource_suffix}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_kubernetes_cluster" "this" {
  name                = "aks-${local.resource_suffix}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  dns_prefix          = "mbcode-${var.environment}"
  kubernetes_version  = "1.29.7"
  sku_tier            = "Standard"

  role_based_access_control_enabled = true
  local_account_disabled            = true
  azure_policy_enabled              = true

  default_node_pool {
    name       = "system"
    node_count = var.aks_node_count
    vm_size    = "Standard_D4s_v5"
    os_disk_size_gb = 128
    zones           = [1, 2, 3]
    type            = "VirtualMachineScaleSets"
    mode            = "System"
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  kubelet_identity {
    client_id                 = azurerm_user_assigned_identity.aks.client_id
    object_id                 = azurerm_user_assigned_identity.aks.principal_id
    user_assigned_identity_id = azurerm_user_assigned_identity.aks.id
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  }

  tags = {
    environment = var.environment
    app         = var.project_name
  }
}

resource "azurerm_role_assignment" "acr_pull" {
  principal_id         = azurerm_kubernetes_cluster.this.kubelet_identity[0].object_id
  role_definition_name = "AcrPull"
  scope                = azurerm_container_registry.this.id
}

resource "azurerm_postgresql_flexible_server" "this" {
  name                          = "psql${local.resource_suffix}"
  location                      = azurerm_resource_group.this.location
  resource_group_name           = azurerm_resource_group.this.name
  sku_name                      = "B_Standard_B2s"
  version                       = "16"
  administrator_login           = var.db_admin_login
  administrator_password        = var.db_admin_password
  zone                          = "1"
  storage_mb                    = 32768
  backup_retention_days         = 7
  public_network_access_enabled = true

  lifecycle {
    ignore_changes = [zone]
  }

  tags = {
    environment = var.environment
    app         = var.project_name
  }
}

resource "azurerm_postgresql_flexible_server_database" "mbcode" {
  name      = "mbcode"
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
