# OneLake Folder-Level Permission Management Demo (Azure Static Web Apps)

## 1. Overview

This project is a demo app for folder-level permission management on Microsoft Fabric OneLake.

It uses:

- Microsoft Entra ID for user sign-in
- Azure Static Web Apps for hosting frontend + Python API
- React 18.2 + Vite 5.0 + React Router 6.20 for frontend SPA
- @azure/msal-react 2.0 for Entra ID authentication UI flow
- A local mapping file for `user -> service principal`
- Azure Key Vault for service principal secret details
- OneLake file operations through the official OneLake-supported Python SDK pattern (`azure-storage-file-datalake` + Entra auth)

After sign-in, the app maps the user to a specific service principal and folder, then loads files with that principal's permission boundary.

## 2. Implemented Features

- Entra ID sign-in / sign-out
- User-to-service-principal mapping from config file (UPN -> SP secret name)
- Service principal details loaded from Azure Key Vault
- Folder-level access control enforced by Fabric OneLake permissions (not code)
- File list in folder: name, modified time, type, size
- Multi-file upload with visible upload progress
- Multi-select download as ZIP
- OneLake SDK enforces permissions: if user's SP lacks access to a folder, OneLake returns permission error

## 3. High-Level Architecture

- Frontend: `frontend/` (React + Vite)
- Backend API: `api/` (Python Azure Functions)
- Mapping source: `api/config/user_sp_mapping.json`
- Secrets source: Azure Key Vault secrets (JSON payload)

## 4. Logical Flow Diagram

This architecture reflects the current implementation and Azure service chain:

`User -> Azure Static Web Apps -> Azure Functions -> Azure Key Vault -> Microsoft Fabric Lakehouse (OneLake)`

Rendered diagram (PNG):

![Azure Architecture Diagram](architecture-azure-minimal.png)

Editable source (draw.io):

- `architecture-azure-minimal.drawio`

Open the draw.io file in VS Code with the Draw.io extension to edit the architecture diagram.

**Key Flow:**
1. User accesses the frontend hosted on Azure Static Web Apps.
2. User authentication is handled through Microsoft Entra ID.
3. Frontend calls Azure Functions APIs for file operations.
4. Function app reads user-to-service-principal mapping from local config.
5. Function app fetches service principal credentials from Azure Key Vault.
6. Function app calls Fabric Lakehouse (OneLake) via SDK using mapped SP credentials.
7. OneLake enforces folder-level permissions and returns success or permission denied.
8. Function app returns the result to frontend for display.

## 5. User Mapping File

File: `api/config/user_sp_mapping.json`

This file maps Entra ID user UPN to a Key Vault secret name that contains the service principal credentials. The mapping is simple and does not include folder or permission information.

```json
{
  "users": {
    "user01@contoso.com": "sp-user01-onelake",
    "user02@contoso.com": "sp-user02-onelake"
  }
}
```

**Important:** Actual folder-level permissions are managed through Fabric OneLake UI, not this config file. See section 7 below.

## 6. Folder-Level Permission Configuration in Fabric

All folder-level access control is enforced by Fabric OneLake, not by the application code. This is the recommended security approach.

### Steps:

1. In Fabric workspace, open your lakehouse.
2. Navigate to the **Files** section.
3. For each folder (e.g., `customer01`, `customer02`, ...):
   - Right-click the folder → **Manage access**
   - Add each service principal with desired permission:
     - **Read**: Can list files and download
     - **Write**: Can list, download, upload, delete files
4. The application will enforce these permissions at the OneLake SDK level.

### Security Notes:

- The app code does not validate or restrict folder access; it relies entirely on OneLake permissions.
- If a service principal lacks permission to a folder, the OneLake SDK will raise an error.
- Always configure permissions in Fabric UI for clear auditing and compliance.

## 7. Key Vault Secret JSON Schema

Each `service_principal_secret_name` points to one Key Vault secret. The secret value must be JSON:

```json
{
  "tenant_id": "<tenant-guid>",
  "client_id": "<service-principal-client-id>",
  "client_secret": "<service-principal-client-secret>",
  "onelake_account_name": "onelake",
  "workspace_name": "<fabric-workspace-name>",
  "lakehouse_name": "<fabric-lakehouse-name>",
  "root_path": "<lakehouse>.Lakehouse/Files"
}
```

Notes:

- `root_path` is optional. If omitted, default is `<lakehouse_name>.Lakehouse/Files`.
- The API enforces that user can only access the mapped folder.

## 8. API Endpoints

- `GET /api/profile` - Returns authenticated user info
- `GET /api/folders` - Returns list of available folders for user to try accessing
- `GET /api/files?folder=<folderName>` - Lists files in the specified folder (OneLake enforces SP permissions)
- `POST /api/upload?folder=<folderName>` (multipart form field name: `files`) - Uploads files (OneLake enforces SP write permission)
- `POST /api/download?folder=<folderName>` (JSON body: `{ "files": ["a.txt", "b.csv"] }`) - Downloads files as ZIP (OneLake enforces SP read permission)

## 9. Local Development

Use the dedicated hands-on guide in `HANDS_ON.md`.

Quick start (React frontend):

1. Prepare API settings:
  - Copy `api/local.settings.sample.json` to `api/local.settings.json`.
  - Fill `KEY_VAULT_URL` and optional local-dev auth values.
2. Install dependencies:

```bash
cd frontend
npm install
cd ..\api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Start API (terminal 1):

```bash
cd api
func start
```

4. Start Vite dev server (terminal 2):

```bash
cd frontend
npm run dev
```

5. Start SWA local proxy (terminal 3):

```bash
swa start http://localhost:5173 --api-location api --app-location frontend
```

6. Open `http://localhost:4280` in browser and test sign-in, folder browse, upload, and download.

## 10. Security Notes

- Never store service principal secrets in source code.
- Use Key Vault access control and least privilege.
- Restrict Key Vault access to the app's managed identity in cloud.
- Always configure folder permissions in Fabric OneLake UI for clear governance and compliance.
