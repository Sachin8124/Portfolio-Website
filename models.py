from typing import Any

from database import Field


class SheetModel:
    __fields__: list[str] = []

    def __init__(self, **values: Any):
        for field in self.__fields__:
            setattr(self, field, values.get(field))


def _model(name: str, fields: list[str]) -> type[SheetModel]:
    namespace = {field: Field(field) for field in fields}
    namespace["__fields__"] = fields
    return type(name, (SheetModel,), namespace)


COMMON = ["id", "created_at"]
Project = _model("Project", COMMON + ["title", "description", "category", "tags", "image_url", "external_url"])
Skill = _model("Skill", COMMON + ["name", "category", "proficiency", "icon"])
Website = _model("Website", COMMON + ["title", "url", "description", "image_url", "category"])
Blog = _model("Blog", COMMON + ["title", "summary", "content", "category", "tags", "url", "image_url"])
Certification = _model("Certification", COMMON + ["title", "issuer", "issue_date", "credential_url", "image_url"])
CourseLicense = _model("CourseLicense", COMMON + ["title", "institution", "license_number", "credential_url"])
Photo = _model("Photo", COMMON + ["title", "caption", "image_url", "category"])
LinkUrl = _model("LinkUrl", COMMON + ["title", "url", "platform", "icon"])
ContactMessage = _model("ContactMessage", ["id", "created_at", "full_name", "email", "mobile", "subject", "message", "status", "admin_response", "responded_at"])
AdminUser = _model("AdminUser", COMMON + ["username", "password_hash", "password_changed_at", "updated_at"])
AdminSession = _model("AdminSession", COMMON + ["user_id", "token_hash", "expires_at", "last_seen_at"])
AdminAuditLog = _model("AdminAuditLog", COMMON + ["user_id", "action", "ip_address"])
