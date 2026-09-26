import json
import os
from io import BytesIO
from typing import Any, BinaryIO

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_service() -> Any:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    credentials_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()

    if credentials_json:
        credentials = Credentials.from_service_account_info(
            json.loads(credentials_json), scopes=DRIVE_SCOPES
        )
    elif credentials_file:
        credentials = Credentials.from_service_account_file(
            credentials_file, scopes=DRIVE_SCOPES
        )
    else:
        raise RuntimeError("Google Drive is not configured.")

    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def is_configured() -> bool:
    return bool(
        os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
        and (
            os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
            or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
        )
    )


def _folder_id() -> str:
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID is not configured.")
    return folder_id


def _find_json_file(filename: str) -> dict[str, Any] | None:
    files = _get_service().files().list(
        q=f"'{_folder_id()}' in parents and name = '{filename}' and trashed = false",
        spaces="drive",
        fields="files(id,name,mimeType)",
        pageSize=1,
    ).execute().get("files", [])
    return files[0] if files else None


def read_json_records(filename: str) -> list[dict[str, Any]]:
    file_info = _find_json_file(filename)
    if not file_info:
        return []
    content, _ = download_file(file_info["id"])
    return json.loads(content.decode("utf-8"))


def write_json_records(filename: str, records: list[dict[str, Any]]) -> None:
    from googleapiclient.http import MediaIoBaseUpload

    media = MediaIoBaseUpload(
        BytesIO(json.dumps(records, ensure_ascii=True).encode("utf-8")),
        mimetype="application/json",
        resumable=False,
    )
    service = _get_service()
    file_info = _find_json_file(filename)
    if file_info:
        service.files().update(fileId=file_info["id"], media_body=media).execute()
    else:
        service.files().create(
            body={"name": filename, "parents": [_folder_id()], "mimeType": "application/json"},
            media_body=media,
            fields="id",
        ).execute()


def upload_file(file_obj: BinaryIO, filename: str, content_type: str | None) -> str:
    from googleapiclient.http import MediaIoBaseUpload

    folder_id = _folder_id()

    file_obj.seek(0)
    metadata = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(
        file_obj,
        mimetype=content_type or "application/octet-stream",
        resumable=False,
    )
    result = _get_service().files().create(
        body=metadata,
        media_body=media,
        fields="id,name,mimeType",
    ).execute()
    return result["id"]


def download_file(file_id: str) -> tuple[bytes, str]:
    from googleapiclient.http import MediaIoBaseDownload

    request = _get_service().files().get_media(fileId=file_id)
    content = BytesIO()
    downloader = MediaIoBaseDownload(content, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    metadata = _get_service().files().get(fileId=file_id, fields="mimeType").execute()
    return content.getvalue(), metadata.get("mimeType", "application/octet-stream")
