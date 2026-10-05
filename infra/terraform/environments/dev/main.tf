terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

module "azure_platform" {
  source = "../../modules/azure_platform"

  project_name = "mbcode"
  environment  = "dev"
  location     = "westeurope"
  aks_node_count = 1
  admin_username = "mbcodeadmin"
  admin_password = var.admin_password
  frontdoor_host_name = "dev-mbcode.example.com"
}

variable "admin_password" {
  type      = string
  sensitive = true
}
