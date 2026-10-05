data "azurerm_client_config" "current" {}

locals {
  resource_suffix = lower(replace("${var.project_name}${var.environment}", "-", ""))
  acr_name        = substr(lower(replace("${var.project_name}${var.environment}acr", "-", "")), 0, 50)
  kv_name         = substr(lower(replace("${var.project_name}${var.environment}kv", "-", "")), 0, 24)
  rg_name         = "rg-${var.project_name}-${var.environment}"
  aks_name        = "aks-${var.project_name}-${var.environment}"
  law_name        = "law-${var.project_name}-${var.environment}"
  postgres_name   = "psql-${var.project_name}-${var.environment}"
}

resource "azurerm_resource_group" "this" {
  name     = local.rg_name
  location = var.location

  tags = {
    environment = var.environment
    managed_by  = "terraform"
    app         = var.project_name
  }
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = local.law_name
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
  rbac_authorization_enabled     = true
  soft_delete_retention_days    = 90
  purge_protection_enabled      = true
  public_network_access_enabled = true

  tags = {
    environment = var.environment
    app         = var.project_name
  }
}

resource "azurerm_user_assigned_identity" "aks" {
  name                = "id-${var.project_name}-${var.environment}-aks"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
}

resource "azurerm_kubernetes_cluster" "this" {
  name                = local.aks_name
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  dns_prefix          = "mbcode-${var.environment}"
  sku_tier            = "Standard"
  kubernetes_version  = "1.29.7"

  role_based_access_control_enabled = true
  local_account_disabled            = true
  azure_policy_enabled              = true

  default_node_pool {
    name            = "system"
    node_count      = var.aks_node_count
    vm_size         = "Standard_D4s_v5"
    os_disk_size_gb = 128
    type            = "VirtualMachineScaleSets"
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
  name                          = local.postgres_name
  location                      = azurerm_resource_group.this.location
  resource_group_name           = azurerm_resource_group.this.name
  sku_name                      = "B_Standard_B2s"
  version                       = "16"
  administrator_login           = var.admin_username
  administrator_password        = var.admin_password
  zone                          = "1"
  storage_mb                    = 32768
  backup_retention_days         = 7
  public_network_access_enabled = true

  tags = {
    environment = var.environment
    app         = var.project_name
  }
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "mbcode"
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_cdn_frontdoor_profile" "this" {
  name                = "fdp-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.this.name
  sku_name            = "Standard_AzureFrontDoor"

  tags = {
    environment = var.environment
    app         = var.project_name
  }
}

resource "azurerm_cdn_frontdoor_endpoint" "this" {
  name                     = "fde-${var.project_name}-${var.environment}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.this.id
  enabled                  = true

  tags = {
    environment = var.environment
  }
}

resource "azurerm_cdn_frontdoor_origin_group" "this" {
  name                     = "fog-${var.project_name}-${var.environment}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.this.id
  session_affinity_enabled = true

  health_probe {
    interval_in_seconds = 100
    path                = "/connexion/"
    protocol            = "Https"
    request_type        = "HEAD"
  }

  load_balancing {
    sample_size                        = 4
    successful_samples_required        = 2
    additional_latency_in_milliseconds = 50
  }
}

resource "azurerm_cdn_frontdoor_origin" "aks" {
  name                          = "fo-${var.project_name}-${var.environment}"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.this.id
  enabled                       = true
  host_name                     = "${azurerm_kubernetes_cluster.this.private_fqdn}"
  http_port                     = 80
  https_port                    = 443
  origin_host_header            = "${azurerm_kubernetes_cluster.this.private_fqdn}"
  priority                      = 1
  weight                        = 1000
  certificate_name_check_enabled = true

  private_link {
    request_message      = "AKS ingress private link"
    target_type          = "sites"
    location             = azurerm_resource_group.this.location
    private_link_target_id = azurerm_kubernetes_cluster.this.id
  }
}
