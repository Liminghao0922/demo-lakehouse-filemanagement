import io
import os
import posixpath
import zipfile
from dataclasses import dataclass
from typing import List

from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient

from .keyvault import ServicePrincipalConfig


@dataclass
class FileEntry:
    name: str
    path: str
    modified_time: str
    file_type: str
    size: int


class OneLakeClient:
    def __init__(self, sp_config: ServicePrincipalConfig):
        self._root_path = sp_config.root_path.strip("/")

        credential = ClientSecretCredential(
            tenant_id=sp_config.tenant_id,
            client_id=sp_config.client_id,
            client_secret=sp_config.client_secret,
        )

        account_url = f"https://{sp_config.onelake_account_name}.dfs.fabric.microsoft.com"
        self._service_client = DataLakeServiceClient(account_url=account_url, credential=credential)
        self._filesystem_client = self._service_client.get_file_system_client(sp_config.workspace_name)

    def _resolve_folder_path(self, folder_name: str) -> str:
        folder = folder_name.strip("/")
        return posixpath.join(self._root_path, folder)

    def list_files(self, folder_name: str) -> List[FileEntry]:
        folder_path = self._resolve_folder_path(folder_name)
        items = self._filesystem_client.get_paths(path=folder_path, recursive=False)

        results: List[FileEntry] = []
        for item in items:
            if item.is_directory:
                continue

            name = os.path.basename(item.name)
            ext = os.path.splitext(name)[1].lower().lstrip(".") or "file"
            modified = item.last_modified.isoformat() if item.last_modified else ""
            size = int(item.content_length or 0)

            results.append(
                FileEntry(
                    name=name,
                    path=item.name,
                    modified_time=modified,
                    file_type=ext,
                    size=size,
                )
            )

        results.sort(key=lambda f: f.name.lower())
        return results

    def upload_files(self, folder_name: str, files: list):
        folder_path = self._resolve_folder_path(folder_name)

        for source in files:
            target_path = posixpath.join(folder_path, source.filename)
            target = self._filesystem_client.get_file_client(target_path)
            content = source.stream.read()
            target.upload_data(content, overwrite=True)

    def list_accessible_folders(self) -> List[str]:
        """List all accessible folders (principal directories) under the root path."""
        try:
            items = self._filesystem_client.get_paths(path=self._root_path, recursive=False)
            folders = []
            
            for item in items:
                if item.is_directory:
                    # Extract folder name from full path
                    folder_name = os.path.basename(item.name.rstrip("/"))
                    if folder_name:  # Skip empty names
                        folders.append(folder_name)
            
            folders.sort()
            return folders
        except Exception as exc:
            # If unable to list (permission or path issues), return empty list
            raise Exception(f"Failed to list accessible folders: {exc}")

    def download_as_zip(self, folder_name: str, filenames: List[str]) -> bytes:
        folder_path = self._resolve_folder_path(folder_name)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for filename in filenames:
                safe_name = os.path.basename(filename)
                file_path = posixpath.join(folder_path, safe_name)
                file_client = self._filesystem_client.get_file_client(file_path)
                file_bytes = file_client.download_file().readall()
                zf.writestr(safe_name, file_bytes)

        return zip_buffer.getvalue()
