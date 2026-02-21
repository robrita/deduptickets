#!/usr/bin/env bash
# ============================================================================
# Assign Cosmos DB Built-in Data Contributor role for Entra ID authentication.
#
# Usage:
#   ./scripts/assign_cosmos_role.sh                          # uses .env values
#   ./scripts/assign_cosmos_role.sh --role reader            # override role
#   ./scripts/assign_cosmos_role.sh --principal-id <id>      # specific principal
#
# Options:
#   --account, -a        Cosmos DB account name (default: env COSMOS_ACCOUNT)
#   --resource-group, -g Resource group name (default: env AZURE_RESOURCE_GROUP)
#   --principal-id, -p   Azure AD Object ID (default: env AZURE_PRINCIPAL_ID,
#                        falls back to currently signed-in user)
#   --role, -r           Role to assign: "contributor" (default) or "reader"
#   --help, -h           Show this help message
#
# Environment variables (auto-loaded from .env):
#   COSMOS_ACCOUNT       Cosmos DB account name (overridden by --account)
#   AZURE_RESOURCE_GROUP Resource group name (overridden by --resource-group)
#   AZURE_PRINCIPAL_ID   Principal ID (overridden by --principal-id)
# ============================================================================
set -euo pipefail

# Source .env if present (project root = script dir's parent)
ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck source=/dev/null
    source <(sed 's/\r$//' "$ENV_FILE")
    set +a
fi

ROLE="contributor"
ACCOUNT="${COSMOS_ACCOUNT:-}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-}"
PRINCIPAL_ID="${AZURE_PRINCIPAL_ID:-}"

usage() {
    sed -n '3,21p' "$0" | sed 's/^# \?//'
    exit 0
}

die() { echo "ERROR: $1" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --account|-a)    ACCOUNT="$2";        shift 2 ;;
        --resource-group|-g) RESOURCE_GROUP="$2"; shift 2 ;;
        --principal-id|-p)   PRINCIPAL_ID="$2";   shift 2 ;;
        --role|-r)       ROLE="$2";           shift 2 ;;
        --help|-h)       usage ;;
        *)               die "Unknown option: $1" ;;
    esac
done

# --- Validate required args ------------------------------------------------
[[ -n "$ACCOUNT" ]]        || die "--account is required"
[[ -n "$RESOURCE_GROUP" ]] || die "--resource-group is required"

# --- Resolve role definition name ------------------------------------------
case "$ROLE" in
    contributor) ROLE_NAME="Cosmos DB Built-in Data Contributor" ;;
    reader)      ROLE_NAME="Cosmos DB Built-in Data Reader" ;;
    *)           die "Invalid role '$ROLE'. Use 'contributor' or 'reader'." ;;
esac

# --- Resolve principal ID ---------------------------------------------------
if [[ -z "$PRINCIPAL_ID" ]]; then
    echo "No --principal-id specified. Using currently signed-in user..."
    PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv) \
        || die "Failed to get signed-in user. Run 'az login' first."
    echo "Resolved principal ID: $PRINCIPAL_ID"
fi

# --- Check if role assignment already exists --------------------------------
echo ""
echo "Checking existing role assignments..."
EXISTING=$(az cosmosdb sql role assignment list \
    --account-name "$ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?principalId=='$PRINCIPAL_ID'] | length(@)" \
    -o tsv 2>/dev/null || echo "0")

if [[ "$EXISTING" -gt 0 ]]; then
    echo "Principal already has $EXISTING role assignment(s) on this account."
    echo "Listing current assignments:"
    az cosmosdb sql role assignment list \
        --account-name "$ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?principalId=='$PRINCIPAL_ID'].{RoleDefinitionId:roleDefinitionId, Scope:scope}" \
        -o table
    echo ""
    read -rp "Continue and add the '$ROLE_NAME' role anyway? [y/N] " CONFIRM
    [[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
fi

# --- Assign the role --------------------------------------------------------
echo ""
echo "Assigning role: '$ROLE_NAME'"
echo "  Account:        $ACCOUNT"
echo "  Resource Group:  $RESOURCE_GROUP"
echo "  Principal ID:    $PRINCIPAL_ID"
echo "  Scope:           /"
echo ""

az cosmosdb sql role assignment create \
    --account-name "$ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --role-definition-name "$ROLE_NAME" \
    --principal-id "$PRINCIPAL_ID" \
    --scope "/"

echo ""
echo "Role '$ROLE_NAME' assigned successfully."
