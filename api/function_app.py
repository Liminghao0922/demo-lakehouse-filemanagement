import json
from http import HTTPStatus

import azure.functions as func

from shared.auth import get_user_upn
from shared.keyvault import KeyVaultConfigError, load_service_principal_config
from shared.mapping import MappingNotFoundError, load_user_mapping
from shared.onelake_client import OneLakeClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _json_response(payload: dict, status_code: int = HTTPStatus.OK) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload),
        status_code=status_code,
        mimetype="application/json",
    )


def _build_client(req: func.HttpRequest) -> tuple[str, OneLakeClient] | tuple[None, func.HttpResponse]:
    user_upn = get_user_upn(req)
    if not user_upn:
        return None, func.HttpResponse("Unauthorized", status_code=HTTPStatus.UNAUTHORIZED)

    try:
        mapping = load_user_mapping(user_upn.lower())
        sp_config = load_service_principal_config(mapping.service_principal_secret_name)
    except MappingNotFoundError as exc:
        return None, _json_response({"error": str(exc)}, status_code=HTTPStatus.FORBIDDEN)
    except KeyVaultConfigError as exc:
        return None, _json_response({"error": str(exc)}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    except Exception as exc:
        return None, _json_response({"error": f"Failed to load user/SP configuration: {exc}"}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    client = OneLakeClient(sp_config=sp_config)
    return user_upn, client


@app.route(route="profile", methods=["GET"])
def profile(req: func.HttpRequest) -> func.HttpResponse:
    user_upn, client_or_response = _build_client(req)
    if not user_upn:
        return client_or_response

    return _json_response({"user": user_upn})


@app.route(route="folders", methods=["GET"])
def folders(req: func.HttpRequest) -> func.HttpResponse:
    user_upn, client_or_response = _build_client(req)
    if not user_upn:
        return client_or_response

    try:
        # Dynamically list folders accessible to the service principal
        available_folders = client_or_response.list_accessible_folders()
    except Exception as exc:
        return _json_response({"error": f"Failed to retrieve accessible folders: {exc}"}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    return _json_response({"folders": available_folders})


@app.route(route="files", methods=["GET"])
def files(req: func.HttpRequest) -> func.HttpResponse:
    user_upn, client_or_response = _build_client(req)
    if not user_upn:
        return client_or_response

    folder = req.params.get("folder")
    if not folder:
        return _json_response({"error": "Missing 'folder' parameter."}, status_code=HTTPStatus.BAD_REQUEST)

    try:
        file_entries = client_or_response.list_files(folder_name=folder)
    except Exception as exc:
        # Could be permission denied, not found, or other OneLake error
        return _json_response({"error": f"Failed to list files: {exc}"}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    payload = {
        "folder": folder,
        "files": [
            {
                "name": f.name,
                "path": f.path,
                "modifiedTime": f.modified_time,
                "type": f.file_type,
                "size": f.size,
            }
            for f in file_entries
        ],
    }

    return _json_response(payload)


@app.route(route="upload", methods=["POST"])
def upload(req: func.HttpRequest) -> func.HttpResponse:
    user_upn, client_or_response = _build_client(req)
    if not user_upn:
        return client_or_response

    folder = req.params.get("folder")
    if not folder:
        return _json_response({"error": "Missing 'folder' parameter."}, status_code=HTTPStatus.BAD_REQUEST)

    try:
        files = req.files.getlist("files")
        if not files:
            return _json_response({"error": "No files were uploaded."}, status_code=HTTPStatus.BAD_REQUEST)

        client_or_response.upload_files(folder_name=folder, files=files)
        return _json_response({"message": "Upload completed."})
    except Exception as exc:
        # Could be permission denied or other OneLake error
        return _json_response({"error": f"Failed to upload files: {exc}"}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


@app.route(route="download", methods=["POST"])
def download(req: func.HttpRequest) -> func.HttpResponse:
    user_upn, client_or_response = _build_client(req)
    if not user_upn:
        return client_or_response

    folder = req.params.get("folder")
    if not folder:
        return _json_response({"error": "Missing 'folder' parameter."}, status_code=HTTPStatus.BAD_REQUEST)

    try:
        body = req.get_json()
        filenames = body.get("files", [])
        if not filenames:
            return _json_response({"error": "No files selected."}, status_code=HTTPStatus.BAD_REQUEST)

        archive = client_or_response.download_as_zip(folder_name=folder, filenames=filenames)
        headers = {
            "Content-Disposition": 'attachment; filename="selected-files.zip"',
            "Content-Type": "application/zip",
        }
        return func.HttpResponse(body=archive, status_code=HTTPStatus.OK, headers=headers)
    except Exception as exc:
        # Could be permission denied or other OneLake error
        return _json_response({"error": f"Failed to download files: {exc}"}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
