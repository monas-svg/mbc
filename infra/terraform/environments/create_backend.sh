#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 -g <resource-group> -l <location> -s <storage-account> [-c <container>]

Creates an Azure Storage Account and a container for Terraform remote state,
then writes infra/terraform/environments/backend.tf with the appropriate values.

Requires: `az` CLI logged in (run `az login`) and sufficient permissions.
EOF
}

while getopts ":g:l:s:c:h" opt; do
  case ${opt} in
    g) RG=${OPTARG} ;;
    l) LOCATION=${OPTARG} ;;
    s) STORAGE=${OPTARG} ;;
    c) CONTAINER=${OPTARG} ;;
    h) usage; exit 0 ;;
    :) echo "Missing option for -${OPTARG}"; usage; exit 1 ;;
    \?) echo "Invalid option: -${OPTARG}"; usage; exit 1 ;;
  esac
done

: "${RG:?Need -g resource group}"
: "${LOCATION:?Need -l location}"
: "${STORAGE:?Need -s storage account name}"
CONTAINER=${CONTAINER:-tfstate}

echo "Creating resource group $RG in $LOCATION (if not exists)..."
az group create -n "$RG" -l "$LOCATION"

echo "Creating storage account $STORAGE (Standard_LRS)..."
az storage account create -n "$STORAGE" -g "$RG" -l "$LOCATION" --sku Standard_LRS --kind StorageV2 || true

echo "Creating container $CONTAINER..."
# get account key to create container
KEY=$(az storage account keys list -g "$RG" -n "$STORAGE" --query '[0].value' -o tsv)
az storage container create --name "$CONTAINER" --account-name "$STORAGE" --account-key "$KEY" || true

BACKEND_FILE="$(dirname "$0")/backend.tf"
cat > "$BACKEND_FILE" <<EOF
terraform {
  backend "azurerm" {
    resource_group_name  = "$RG"
    storage_account_name = "$STORAGE"
    container_name       = "$CONTAINER"
    key                  = "dev.tfstate"
  }
}
EOF

echo "Backend written to $BACKEND_FILE"
echo "Done. You can run: terraform init -reconfigure in infra/terraform/environments/dev"
