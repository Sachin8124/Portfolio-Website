from datetime import datetime
import re
from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ==============================================================================
# Projects Schemas
# ==============================================================================
class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = "General"
    tags: Optional[str] = ""
    image_url: Optional[str] = None
    external_url: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    image_url: Optional[str] = None
    external_url: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# Skills Schemas
# ==============================================================================
class SkillBase(BaseModel):
    name: str
    category: Optional[str] = "Technical"
    proficiency: Optional[str] = "Intermediate"
    icon: Optional[str] = "fa-solid fa-code"

class SkillCreate(SkillBase):
    pass

class SkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    proficiency: Optional[str] = None
    icon: Optional[str] = None

class SkillResponse(SkillBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# Websites Schemas
# ==============================================================================
class WebsiteBase(BaseModel):
    title: str
    url: str
    description: Optional[str] = ""
    image_url: Optional[str] = None
    category: Optional[str] = "Portfolio"

class WebsiteCreate(WebsiteBase):
    pass

class WebsiteUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None

class WebsiteResponse(WebsiteBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# Blogs Schemas
# ==============================================================================
class BlogBase(BaseModel):
    title: str
    summary: Optional[str] = ""
    content: Optional[str] = ""
    category: Optional[str] = "General"
    tags: Optional[str] = ""
    url: Optional[str] = None
    image_url: Optional[str] = None

class BlogCreate(BlogBase):
    pass

class BlogUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None

class BlogResponse(BlogBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# Certifications Schemas
# ==============================================================================
class CertificationBase(BaseModel):
    title: str
    issuer: str
    issue_date: Optional[str] = None
    credential_url: Optional[str] = None
    image_url: Optional[str] = None

class CertificationCreate(CertificationBase):
    pass

class CertificationUpdate(BaseModel):
    title: Optional[str] = None
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    credential_url: Optional[str] = None
    image_url: Optional[str] = None

class CertificationResponse(CertificationBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# Courses & Licenses Schemas
# ==============================================================================
class CourseLicenseBase(BaseModel):
    title: str
    institution: str
    license_number: Optional[str] = None
    credential_url: Optional[str] = None

class CourseLicenseCreate(CourseLicenseBase):
    pass

class CourseLicenseUpdate(BaseModel):
    title: Optional[str] = None
    institution: Optional[str] = None
    license_number: Optional[str] = None
    credential_url: Optional[str] = None

class CourseLicenseResponse(CourseLicenseBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# Photos Schemas
# ==============================================================================
class PhotoBase(BaseModel):
    title: str
    caption: Optional[str] = ""
    image_url: str
    category: Optional[str] = "Gallery"

class PhotoCreate(PhotoBase):
    pass

class PhotoUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None

class PhotoResponse(PhotoBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# Links / URLs Schemas
# ==============================================================================
class LinkUrlBase(BaseModel):
    title: str
    url: str
    platform: Optional[str] = "Web"
    icon: Optional[str] = "fa-solid fa-link"

class LinkUrlCreate(LinkUrlBase):
    pass

class LinkUrlUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    platform: Optional[str] = None
    icon: Optional[str] = None

class LinkUrlResponse(LinkUrlBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# Contact Messages Schemas
# ==============================================================================
class ContactMessageCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=3, max_length=254)
    mobile: Optional[str] = Field(default=None, max_length=50)
    subject: Optional[str] = Field(default=None, max_length=200)
    message: str = Field(min_length=10, max_length=5000)

    @field_validator("full_name", "message", mode="before")
    @classmethod
    def strip_required_text(cls, value):
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value):
        if not isinstance(value, str):
            return value
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("mobile", "subject", mode="before")
    @classmethod
    def strip_optional_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value or None


class ContactMessageUpdate(BaseModel):
    status: Literal["pending", "accepted", "answered", "declined"]
    admin_response: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("admin_response", mode="before")
    @classmethod
    def clean_response(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value or None

class ContactMessageResponse(BaseModel):
    full_name: str
    email: str
    mobile: Optional[str] = None
    subject: Optional[str] = None
    message: str
    id: int
    status: Literal["pending", "accepted", "answered", "declined"]
    admin_response: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# Admin Authentication Schemas
# ==============================================================================
def validate_admin_password(value: str) -> str:
    if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or not re.search(r"\d", value) or not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must include uppercase, lowercase, number, and special character")
    return value

class AdminSetupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=12, max_length=128)

    _validate_password = field_validator("password")(validate_admin_password)

class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=128)

class AdminPasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    _validate_password = field_validator("new_password")(validate_admin_password)

class AdminRecoveryRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    recovery_key: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)

    _validate_password = field_validator("new_password")(validate_admin_password)

class AdminAuthResponse(BaseModel):
    authenticated: bool
    setup_required: bool = False
    password_expired: bool = False
    username: Optional[str] = None
    password_expires_at: Optional[datetime] = None

# ==============================================================================
# Machine Learning Schemas
# ==============================================================================
class MLCategorizeRequest(BaseModel):
    title: Optional[str] = ""
    description: Optional[str] = ""
    text: Optional[str] = ""

class MLCategorizeResponse(BaseModel):
    category: str
    confidence: float
    suggested_tags: List[str]
    category_scores: Dict[str, float]
