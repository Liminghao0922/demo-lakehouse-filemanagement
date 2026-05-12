# Hands-On Guide

## 1. Prerequisites

- Azure subscription with Azure Static Web Apps and Key Vault access
- Microsoft Fabric workspace and lakehouse
- Two Microsoft Entra test users (example: `user01@contoso.com`, `user02@contoso.com`)
- Two service principals with OneLake folder-level permissions
- Python 3.10+
- Node.js 18+
- Azure Functions Core Tools v4
- SWA CLI

Install SWA CLI:

```bash
npm install -g @azure/static-web-apps-cli
```

### Minimum App Registration Checklist (Web Login)

Before local or cloud sign-in tests, prepare one Microsoft Entra app registration for the React MSAL frontend:

1. Create an app registration (single-tenant recommended for internal demo).
2. Add platform type: **Single-page application (SPA)**.
3. Configure redirect URIs:
  - `http://localhost:4280` (recommended local URI when accessing through SWA CLI)
  - `http://localhost:5173` (optional, only when testing Vite directly)
  - `https://<your-static-web-app-domain>` (production)
4. Grant delegated permissions: `openid`, `profile`, `email` (and `User.Read` if required by tenant policy).
5. Put values into frontend env:
  - `VITE_AZURE_CLIENT_ID` = Application (client) ID
  - `VITE_AZURE_TENANT_ID` = Directory (tenant) ID
  - `VITE_AZURE_REDIRECT_URI` = `http://localhost:4280` for the local SWA flow

Note: This checklist is for MSAL browser login. You still need to configure Entra ID provider in Azure Static Web Apps Authentication.

## 2. Prepare Service Principals

Create two service principals in Microsoft Entra ID. You will use their client IDs and secrets for OneLake access.

### Steps

1. Open Azure CLI or Azure Portal, then create the first service principal:

```bash
az ad sp create-for-rbac --name "sp-onelake-user01" --skip-assignment
```

For this demo, do not grant Azure subscription RBAC roles (such as Contributor). OneLake folder permissions are configured in Fabric UI. The output will show:
- `appId` (this is the client ID)
- `password` (this is the client secret)
- `tenant` (this is the tenant ID)

Save these values securely.

2. Create the second service principal:

```bash
az ad sp create-for-rbac --name "sp-onelake-user02" --skip-assignment
```

3. Note down the credentials for both SPs:
   - SP01: appId, password, tenant
   - SP02: appId, password, tenant

4. (Optional) If you need to reset the password for an existing SP:

```bash
az ad sp credential reset --id <appId> --append
```

5. Verify the service principal was created:

```bash
az ad sp show --id <appId>
```

## 3. Prepare OneLake Folders and Permissions

Create folders in your Fabric lakehouse and configure folder-level permissions for each service principal.

### Steps

1. Sign in to [Fabric.microsoft.com](https://fabric.microsoft.com).

2. Open your workspace and navigate to the lakehouse.

3. In the **Files** section, create the following folders by right-clicking and selecting **New Folder**:
   - `customer01`
   - `customer02`
   - `customer03` (optional, for read-only demo)

4. For each folder, configure folder-level access:

   **For customer01 (SP01 - Read & Write):**
   - Right-click `customer01` → **Manage access**
   - Click **+ Add permissions**
   - Enter SP01's app ID (from service principal creation)
   - Select **Read** and **Write** permissions
   - Click **Save**

   **For customer02 (SP02 - Read & Write):**
   - Right-click `customer02` → **Manage access**
   - Click **+ Add permissions**
   - Enter SP02's app ID
   - Select **Read** and **Write** permissions
   - Click **Save**

   **For customer03 (Optional - Read-only demo):**
   - Right-click `customer03` → **Manage access**
   - Click **+ Add permissions**
   - Enter SP01's or SP02's app ID
   - Select **Read** only (no Write)
   - Click **Save**

5. Verify permissions are set correctly. You can see the list of users/SPs with access by clicking **Manage access** again.

6. (Optional) Add some sample files to test:
   - Upload a few test files to `customer01`, `customer02`, etc.
   - These will help verify the app is working correctly

## 4. Prepare Key Vault Secrets

Create one secret per service principal in Azure Key Vault, where the secret value is a JSON object containing SP credentials.

### Steps

1. Ensure you have an Azure Key Vault. If not, create one:

```bash
az keyvault create --name "kv-onelake-demo" --resource-group "<your-resource-group>" --location <region>
```

2. Create the first Key Vault secret for SP01:

```bash
az keyvault secret set --vault-name "kv-onelake-demo" --name "sp-user01-onelake" --value '{
  "tenant_id": "<tenant-guid>",
  "client_id": "<sp01-appId>",
  "client_secret": "<sp01-password>",
  "onelake_account_name": "onelake",
  "workspace_name": "<fabric-workspace-name>",
  "lakehouse_name": "<fabric-lakehouse-name>",
  "root_path": "<fabric-lakehouse-name>.Lakehouse/Files"
}'
```

Replace placeholders:
- `<tenant-guid>`: Your Azure AD tenant ID (from SP creation output)
- `<sp01-appId>`: The appId from SP01 creation
- `<sp01-password>`: The password from SP01 creation
- `<fabric-workspace-name>`: Your Fabric workspace name
- `<fabric-lakehouse-name>`: Your Fabric lakehouse name

3. Create the second Key Vault secret for SP02:

```bash
az keyvault secret set --vault-name "kv-onelake-demo" --name "sp-user02-onelake" --value '{
  "tenant_id": "<tenant-guid>",
  "client_id": "<sp02-appId>",
  "client_secret": "<sp02-password>",
  "onelake_account_name": "onelake",
  "workspace_name": "<fabric-workspace-name>",
  "lakehouse_name": "<fabric-lakehouse-name>",
  "root_path": "<fabric-lakehouse-name>.Lakehouse/Files"
}'
```

4. Verify the secrets were created:

```bash
az keyvault secret list --vault-name "kv-onelake-demo"
```

5. To retrieve a secret value for verification:

```bash
az keyvault secret show --vault-name "kv-onelake-demo" --name "sp-user01-onelake"
```

## 5. Configure User Mapping

Recommended for deployment: store mapping JSON in Key Vault and use local file as fallback for development.

1. Create a Key Vault secret for user mapping:

```bash
az keyvault secret set --vault-name "kv-onelake-demo" --name "user-sp-mapping" --value '{
  "users": {
    "user01@contoso.com": "sp-user01-onelake",
    "user02@contoso.com": "sp-user02-onelake"
  }
}'
```

2. (Optional local fallback) Edit `api/config/user_sp_mapping.json`:

Edit `api/config/user_sp_mapping.json` to map Entra ID users to Key Vault secret names:

```json
{
  "users": {
    "user01@contoso.com": "sp-user01-onelake",
    "user02@contoso.com": "sp-user02-onelake"
  }
}
```

Notes:
- The mapping is UPN -> SP secret name only.
- Folder-level permissions are already configured in Fabric OneLake UI (step 3).
- The app will enforce these OneLake permissions at runtime.
- Runtime order is: Key Vault mapping secret -> local file fallback.

## 6. Local Run

### Prerequisites

- Azure CLI installed and logged in:
  ```bash
  az login
  ```

- If using local Key Vault access, ensure your Azure CLI account has permissions to read Key Vault secrets.

### Steps

1. Copy the settings template:

```bash
copy api\local.settings.sample.json api\local.settings.json
```

2. Update `api/local.settings.json` with your Key Vault URL and configuration:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "KEY_VAULT_URL": "https://kv-onelake-demo.vault.azure.net/",
    "USER_SP_MAPPING_SECRET_NAME": "user-sp-mapping",
    "USER_SP_MAPPING_FILE": "config/user_sp_mapping.json",
    "USER_SP_MAPPING_ALLOW_FILE_FALLBACK": "true",
    "ALLOW_LOCAL_DEV_AUTH": "true",
    "DEV_USER_UPN": "user01@contoso.com"
  }
}
```

Replace `kv-onelake-demo` with your actual Key Vault name.

**Important:** When `ALLOW_LOCAL_DEV_AUTH=true`, the app will use `DEV_USER_UPN` instead of Entra ID. This is for local development only.

3. Install Python dependencies:

```bash
cd api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

4. Run Azure Functions API in one terminal:

```bash
cd api
func start
```

You should see output like:
```
Azure Functions Core Tools
...
Now listening on: http://0.0.0.0:7071
```

5. In a new terminal, run the SWA CLI for frontend + local proxy:

```bash
swa start http://localhost:5173 --api-location api --app-location frontend
```

The command will start:
- Frontend dev server on port 5173
- Local static web app (SWA) auth/proxy on port 4280

You should see output showing:
```
...
Welcome to Azure Static Web Apps CLI!
...
Local server running at http://localhost:4280
```

6. Open the URL shown (typically `http://localhost:4280`) in your browser.

7. The app will:
   - Auto-detect you're logged in as `user01@contoso.com` (due to local dev settings)
   - Show session info
   - Let you select folders and browse files

8. To test with different users, change `DEV_USER_UPN` in `local.settings.json` and restart the Functions host.

### Troubleshooting

- **"Failed to list files"**: Check that the SP has permission in Fabric OneLake for the folder.
- **"Unauthorized"**: Ensure `ALLOW_LOCAL_DEV_AUTH=true` and `DEV_USER_UPN` is set.
- **Key Vault authentication error**: Run `az login` to ensure your CLI is authenticated.

## 7. Deploy to Azure Static Web Apps + Linked Azure Functions Backend

### Steps

1. Create an Azure Static Web App resource (if you don't have one):

```bash
az staticwebapp create \
  --name "swa-onelake-demo" \
  --resource-group "<your-resource-group>" \
  --location "<region>" \
  --source "https://github.com/<your-github-username>/<repo-name>" \
  --branch "main" \
  --app-location "frontend" \
  --api-location "" \
  --output-location "dist"
```

2. Deploy the backend as a separate Azure Functions app.

3. In Azure Portal, go to your Static Web App → **APIs**:

   - Under **Production**, select **Link**.
   - Choose **Function App**.
   - Select your Azure Functions app.
   - Confirm the link.

4. In Azure Portal, go to your Functions app → **Identity** and enable managed identity.

5. In Azure Portal, go to your Functions app → **Configuration** and add:
   - `KEY_VAULT_URL`: `https://kv-onelake-demo.vault.azure.net/`
   - `USER_SP_MAPPING_SECRET_NAME`: `user-sp-mapping`
   - `USER_SP_MAPPING_ALLOW_FILE_FALLBACK`: `false`

   Optional local-style fallback in cloud:
   - `USER_SP_MAPPING_FILE`: `config/user_sp_mapping.json`

6. Grant the Functions app's managed identity access to Key Vault:

```bash
# Get the Functions app's managed identity (principal ID)
PRINCIPAL_ID=$(az functionapp identity show --name "<your-functions-app>" \
  --resource-group "<your-resource-group>" \
  --query "principalId" --output tsv)

# Grant Key Vault secret read access
az keyvault set-policy --name "kv-onelake-demo" \
  --object-id "$PRINCIPAL_ID" \
  --secret-permissions get list
```

7. Configure Entra ID authentication in Static Web Apps:

   - In Azure Portal → **Settings** → **Authentication**
   - Click **Add** → **Entra ID**
   - Fill in app registration details (or create a new one)
   - Set **Restricted access** to **Require authentication**

8. Configure GitHub deployment (if using GitHub):

   - Push your code to GitHub
   - In Azure Portal → **Deployment** → Connect your GitHub repo
  - The provided GitHub Actions workflows will trigger automatically:
    - `.github/workflows/azure-static-web-apps.yml`
    - `.github/workflows/azure-functions-backend.yml`

9. Wait for deployment to complete and verify:

```bash
az staticwebapp show --name "swa-onelake-demo" \
  --resource-group "<your-resource-group>"
```

Once deployment is complete, you can access your app at the generated URL (e.g., `https://swa-onelake-demo.azurestaticapps.net`).

### Troubleshooting

- **403 Forbidden**: Ensure the managed identity has Secret Get/List permissions on Key Vault.
- **Unauthorized (Entra ID)**: Verify the Entra ID app registration is correctly configured in Static Web Apps.
- **"Key Vault not found"**: Ensure `KEY_VAULT_URL` is correctly set in app settings.
- **"Failed to load user mapping configuration"**: Verify `USER_SP_MAPPING_SECRET_NAME` exists and contains valid JSON.
- **API 404 from SWA**: Confirm the Functions app is linked under SWA → APIs and the backend is publicly reachable.

## 8. Validation Checklist

- User01 can access customer01, customer02, customer03 (depending on SP01 permissions in Fabric)
- User02 can access only folders where SP02 has permission (configured in Fabric)
- Upload succeeds when SP has write permission in Fabric
- Upload fails with permission error when SP lacks write permission
- Downloaded ZIP contains all selected files
- Folder-level access is fully controlled by Fabric OneLake permissions, not application logic
