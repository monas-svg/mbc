# Remote state is intentionally kept external to the repo to avoid storing state locally.
# Bootstrap it once in Azure with:
#   az group create --name rg-mbcode-shared --location westeurope
#   az storage account create --name <unique-storage> --resource-group rg-mbcode-shared --location westeurope --sku Standard_LRS
#   az storage container create --name tfstate --account-name <unique-storage>
#
# Then uncomment and adapt the backend block below before first run.
#
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "rg-mbcode-shared"
#     storage_account_name = "mbcodetfstate1234"
#     container_name       = "tfstate"
#     key                  = "mbcode/prod.tfstate"
#   }
# }
