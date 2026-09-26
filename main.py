import os
import hashlib
import hmac
import secrets
import smtplib
from email.message import EmailMessage
from typing import Any, List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, Request, Response, status, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

from database import Session, get_db
import models
import schemas
from ml_categorizer import ml_engine

load_dotenv()

PASSWORD_MAX_AGE_DAYS = 30
SESSION_MAX_AGE_SECONDS = 8 * 60 * 60
SESSION_COOKIE = "portfolio_admin_session"
OWNER_RECOVERY_KEY = os.getenv("OWNER_RECOVERY_KEY", "").strip()
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "PORTFOLIO_ALLOWED_ORIGINS",
        "http://127.0.0.1:8001,http://localhost:8001"
    ).split(",")
    if origin.strip()
]
PUBLIC_API_GET_PREFIXES = (
    "/api/projects", "/api/skills", "/api/websites", "/api/blogs",
    "/api/certifications", "/api/courses", "/api/photos", "/api/links"
)

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def session_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def password_expired(user: Any) -> bool:
    return (datetime.utcnow() - user.password_changed_at).days >= PASSWORD_MAX_AGE_DAYS

def audit(db: Session, action: str, user_id: Optional[int], request: Request):
    db.add(models.AdminAuditLog(
        user_id=user_id,
        action=action,
        ip_address=request.client.host if request.client else None
    ))

def send_contact_emails(msg: schemas.ContactMessageCreate) -> None:
    sender_email = os.getenv("GMAIL_USERNAME", "").strip()
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    recipient_email = os.getenv("GMAIL_RECIPIENT", sender_email).strip()

    if not sender_email or not app_password or not recipient_email:
        raise RuntimeError("Gmail is not configured. Set GMAIL_USERNAME, GMAIL_APP_PASSWORD, and GMAIL_RECIPIENT.")

    notification = EmailMessage()
    notification.set_content(
        f"""
You have received a new inquiry from your portfolio website:

Name: {msg.full_name}
Email: {msg.email}
Mobile: {msg.mobile or 'Not provided'}
Subject: {msg.subject or 'No subject'}

Message:
{msg.message}
        """
    )
    notification["To"] = recipient_email
    notification["From"] = sender_email
    notification["Reply-To"] = msg.email
    notification["Subject"] = f"Portfolio Inquiry: {msg.subject or 'New Message'}"

    acknowledgement = EmailMessage()
    acknowledgement.set_content(
        f"Hello {msg.full_name},\n\n"
        "Thank you for contacting me. I received your inquiry and will reply soon.\n\n"
        "Your message:\n"
        f"{msg.message}\n\n"
        "Best regards"
    )
    acknowledgement["To"] = msg.email
    acknowledgement["From"] = sender_email
    acknowledgement["Subject"] = "Thanks for contacting me"

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(notification)
        server.send_message(acknowledgement)

def current_admin(request: Request, db: Session) -> Optional[Any]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    session = db.query(models.AdminSession).filter(
        models.AdminSession.token_hash == session_hash(token),
        models.AdminSession.expires_at > datetime.utcnow()
    ).first()
    if not session:
        return None
    user = db.query(models.AdminUser).filter(models.AdminUser.id == session.user_id).first()
    if not user or password_expired(user):
        return None
    session.last_seen_at = datetime.utcnow()
    return user

# ==============================================================================
# FastAPI Application & Middleware
# ==============================================================================
app = FastAPI(
    title="Sachin Burman Portfolio Backend",
    description="FastAPI backend with in-memory records and scikit-learn NLP auto-categorization",
    version="1.0.0"
)

# Enable CORS for local and web development
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def protect_admin_api(request: Request, call_next):
    """Temporary dev override: disable admin-only API locking for the portfolio app."""
    return await call_next(request)

# ==============================================================================
# In-memory initial seeder
# ==============================================================================
def seed_initial_data():
    db = next(get_db())
    try:
        # Check if already seeded
        if db.query(models.Project).count() == 0:
            initial_projects = [
                models.Project(
                    title="SE-GUARD Platform",
                    description="Automated vulnerability assessment framework, network intrusion monitoring, and real-time defense platform built with Python.",
                    category="Cyber Security",
                    tags="Cyber Security, SE-GUARD, Vulnerability Assessment, Network Defense",
                    image_url="",
                    external_url="https://github.com/Sachin8124/SE-GUARD"
                ),
                models.Project(
                    title="Food Delivering UI",
                    description="A clean, responsive food ordering mobile and web UI layout designed in Adobe XD with an intuitive cart checkout workflow.",
                    category="Web Design",
                    tags="Web Design, UI/UX Design, Adobe XD, Responsive UI",
                    image_url="",
                    external_url="https://sachinburman.netlify.app/"
                ),
                models.Project(
                    title="Cyber Forensics Report",
                    description="In-depth forensic analysis and structured investigative report on digital evidence extraction using memory analysis tools.",
                    category="Digital Forensics",
                    tags="Digital Forensics, Cyber Forensics, Evidence Analysis, Volatility",
                    image_url="",
                    external_url="https://sachinburman.netlify.app/"
                ),
                models.Project(
                    title="Food Ordering UI",
                    description="Interactive PizzaHut ordering UI designed in Figma featuring custom components and rolling pizza interactions.",
                    category="Web Design",
                    tags="Web Design, Figma, UI/UX Design, Prototyping",
                    image_url="",
                    external_url="https://sachinburman.netlify.app/"
                ),
            ]
            db.add_all(initial_projects)

        if db.query(models.Skill).count() == 0:
            initial_skills = [
                models.Skill(name="HTML5", category="Web Design", proficiency="Expert", icon="fa-brands fa-html5"),
                models.Skill(name="CSS3", category="Web Design", proficiency="Expert", icon="fa-brands fa-css3-alt"),
                models.Skill(name="Python", category="Programming", proficiency="Expert", icon="fa-brands fa-python"),
                models.Skill(name="SQL", category="Database", proficiency="Intermediate", icon="fa-solid fa-database"),
                models.Skill(name="Digital Forensics", category="Cyber Security", proficiency="Advanced", icon="fa-solid fa-fingerprint"),
                models.Skill(name="Responsive UI Design", category="Web Design", proficiency="Expert", icon="fa-solid fa-mobile-screen"),
            ]
            db.add_all(initial_skills)

        if db.query(models.LinkUrl).count() == 0:
            initial_links = [
                models.LinkUrl(title="LinkedIn", url="https://www.linkedin.com/in/sachin-burman-1bb305232", platform="LinkedIn", icon="fa-brands fa-linkedin-in"),
                models.LinkUrl(title="GitHub", url="https://github.com/Sachin8124", platform="GitHub", icon="fa-brands fa-github"),
                models.LinkUrl(title="Instagram", url="https://www.instagram.com/hackingwithsachin?igsi=bjNhbTJhbjFheHk4", platform="Instagram", icon="fa-brands fa-instagram"),
            ]
            db.add_all(initial_links)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error seeding in-memory records: {e}")
    finally:
        db.close()

seed_initial_data()

# ============================================================================== 
# Owner Authentication
# ============================================================================== 
def set_admin_cookie(response: Response, token: str):
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=os.getenv("COOKIE_SECURE", "0") == "1"
    )

@app.get("/api/auth/status", response_model=schemas.AdminAuthResponse, tags=["Admin Auth"])
def auth_status(request: Request, db: Session = Depends(get_db)):
    user = db.query(models.AdminUser).first()
    if not user:
        return schemas.AdminAuthResponse(authenticated=False, setup_required=True)
    active_user = current_admin(request, db)
    return schemas.AdminAuthResponse(
        authenticated=active_user is not None,
        setup_required=False,
        password_expired=password_expired(user),
        username=user.username,
        password_expires_at=user.password_changed_at + timedelta(days=PASSWORD_MAX_AGE_DAYS)
    )

@app.post("/api/auth/setup", response_model=schemas.AdminAuthResponse, tags=["Admin Auth"])
def setup_admin(request: Request, response: Response, setup: schemas.AdminSetupRequest, db: Session = Depends(get_db)):
    if db.query(models.AdminUser).count() > 0:
        raise HTTPException(status_code=409, detail="Admin account is already configured")
    username = setup.username.strip()
    user = models.AdminUser(username=username, password_hash=hash_password(setup.password))
    db.add(user)
    db.flush()
    audit(db, "setup", user.id, request)
    token = secrets.token_urlsafe(48)
    db.add(models.AdminSession(
        user_id=user.id,
        token_hash=session_hash(token),
        expires_at=datetime.utcnow().replace(microsecond=0) + timedelta(seconds=SESSION_MAX_AGE_SECONDS)
    ))
    db.commit()
    set_admin_cookie(response, token)
    return schemas.AdminAuthResponse(authenticated=True, username=user.username, password_expired=False)

@app.post("/api/auth/login", response_model=schemas.AdminAuthResponse, tags=["Admin Auth"])
def login_admin(request: Request, response: Response, credentials: schemas.AdminLoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.AdminUser).filter(models.AdminUser.username == credentials.username.strip()).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        audit(db, "login_failed", user.id if user else None, request)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if password_expired(user):
        raise HTTPException(status_code=403, detail="Password expired. Create a new password to continue.")
    token = secrets.token_urlsafe(48)
    db.add(models.AdminSession(
        user_id=user.id,
        token_hash=session_hash(token),
        expires_at=datetime.utcnow() + timedelta(seconds=SESSION_MAX_AGE_SECONDS)
    ))
    audit(db, "login", user.id, request)
    db.commit()
    set_admin_cookie(response, token)
    return schemas.AdminAuthResponse(authenticated=True, username=user.username, password_expired=False)

@app.post("/api/auth/rotate-password", response_model=schemas.AdminAuthResponse, tags=["Admin Auth"])
def rotate_expired_password(request: Request, response: Response, passwords: schemas.AdminPasswordChangeRequest, db: Session = Depends(get_db)):
    username = request.headers.get("X-Admin-Username", "").strip()
    user = db.query(models.AdminUser).filter(models.AdminUser.username == username).first()
    if not user or not verify_password(passwords.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or current password")
    user.password_hash = hash_password(passwords.new_password)
    user.password_changed_at = datetime.utcnow()
    token = secrets.token_urlsafe(48)
    db.add(models.AdminSession(
        user_id=user.id,
        token_hash=session_hash(token),
        expires_at=datetime.utcnow() + timedelta(seconds=SESSION_MAX_AGE_SECONDS)
    ))
    audit(db, "password_change", user.id, request)
    db.commit()
    set_admin_cookie(response, token)
    return schemas.AdminAuthResponse(authenticated=True, username=user.username, password_expired=False)

@app.post("/api/auth/recover-password", response_model=schemas.AdminAuthResponse, tags=["Admin Auth"])
def recover_owner_password(request: Request, response: Response, recovery: schemas.AdminRecoveryRequest, db: Session = Depends(get_db)):
    """Recover an owner account with a deployment-only secret, without changing the DB schema."""
    if not OWNER_RECOVERY_KEY or not hmac.compare_digest(recovery.recovery_key, OWNER_RECOVERY_KEY):
        raise HTTPException(status_code=401, detail="Recovery key is invalid or not configured")

    user = db.query(models.AdminUser).filter(
        models.AdminUser.username == recovery.username.strip()
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="Recovery key is invalid or not configured")

    user.password_hash = hash_password(recovery.new_password)
    user.password_changed_at = datetime.utcnow()
    db.query(models.AdminSession).filter(models.AdminSession.user_id == user.id).delete()
    audit(db, "password_recovery", user.id, request)

    token = secrets.token_urlsafe(48)
    db.add(models.AdminSession(
        user_id=user.id,
        token_hash=session_hash(token),
        expires_at=datetime.utcnow() + timedelta(seconds=SESSION_MAX_AGE_SECONDS)
    ))
    db.commit()
    set_admin_cookie(response, token)
    return schemas.AdminAuthResponse(authenticated=True, username=user.username, password_expired=False)

@app.post("/api/auth/logout", response_model=schemas.AdminAuthResponse, tags=["Admin Auth"])
def logout_admin(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    user = current_admin(request, db)
    if user:
        audit(db, "logout", user.id, request)
    if token:
        db.query(models.AdminSession).filter(models.AdminSession.token_hash == session_hash(token)).delete()
    db.commit()
    response.delete_cookie(SESSION_COOKIE)
    return schemas.AdminAuthResponse(authenticated=False)

@app.post("/api/auth/change-password", response_model=schemas.AdminAuthResponse, tags=["Admin Auth"])
def change_admin_password(request: Request, response: Response, passwords: schemas.AdminPasswordChangeRequest, db: Session = Depends(get_db)):
    user = current_admin(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    if not verify_password(passwords.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(passwords.new_password)
    user.password_changed_at = datetime.utcnow()
    audit(db, "password_change", user.id, request)
    db.commit()
    return schemas.AdminAuthResponse(authenticated=True, username=user.username, password_expired=False)

# ==============================================================================
# Health Check Endpoint
# ==============================================================================
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "storage": "in_memory",
        "ml_model_loaded": ml_engine.is_trained
    }

# ==============================================================================
# 1. PROJECTS ENDPOINTS (with ML auto-categorization)
# ==============================================================================
@app.get("/api/projects", response_model=List[schemas.ProjectResponse], tags=["Projects"])
def get_projects(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Project)
    if category and category.lower() != "all":
        query = query.filter(models.Project.category.ilike(f"%{category}%"))
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (models.Project.title.ilike(search_fmt)) |
            (models.Project.description.ilike(search_fmt)) |
            (models.Project.tags.ilike(search_fmt))
        )
    return query.order_by(models.Project.id.desc()).all()

@app.get("/api/projects/{project_id}", response_model=schemas.ProjectResponse, tags=["Projects"])
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.post("/api/projects", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED, tags=["Projects"])
def create_project(project_in: schemas.ProjectCreate, db: Session = Depends(get_db)):
    category = project_in.category
    tags = project_in.tags

    # Trigger ML auto-categorization & tagging if category/tags are default or empty
    if not category or category in ["General", ""]:
        ml_res = ml_engine.categorize_and_tag(project_in.title, project_in.description or "")
        category = ml_res["category"]
        if not tags:
            tags = ", ".join(ml_res["suggested_tags"])

    new_project = models.Project(
        title=project_in.title,
        description=project_in.description,
        category=category,
        tags=tags,
        image_url=project_in.image_url,
        external_url=project_in.external_url
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

@app.put("/api/projects/{project_id}", response_model=schemas.ProjectResponse, tags=["Projects"])
def update_project(project_id: int, project_update: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project

@app.delete("/api/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Projects"])
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return None

# ==============================================================================
# 2. SKILLS ENDPOINTS
# ==============================================================================
@app.get("/api/skills", response_model=List[schemas.SkillResponse], tags=["Skills"])
def get_skills(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Skill)
    if category and category.lower() != "all":
        query = query.filter(models.Skill.category.ilike(f"%{category}%"))
    return query.order_by(models.Skill.id.asc()).all()

@app.get("/api/skills/{skill_id}", response_model=schemas.SkillResponse, tags=["Skills"])
def get_skill(skill_id: int, db: Session = Depends(get_db)):
    skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill

@app.post("/api/skills", response_model=schemas.SkillResponse, status_code=status.HTTP_201_CREATED, tags=["Skills"])
def create_skill(skill_in: schemas.SkillCreate, db: Session = Depends(get_db)):
    new_skill = models.Skill(**skill_in.model_dump())
    db.add(new_skill)
    db.commit()
    db.refresh(new_skill)
    return new_skill

@app.put("/api/skills/{skill_id}", response_model=schemas.SkillResponse, tags=["Skills"])
def update_skill(skill_id: int, skill_update: schemas.SkillUpdate, db: Session = Depends(get_db)):
    skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    update_data = skill_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(skill, key, value)

    db.commit()
    db.refresh(skill)
    return skill

@app.delete("/api/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Skills"])
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(skill)
    db.commit()
    return None

# ==============================================================================
# 3. WEBSITES ENDPOINTS
# ==============================================================================
@app.get("/api/websites", response_model=List[schemas.WebsiteResponse], tags=["Websites"])
def get_websites(db: Session = Depends(get_db)):
    return db.query(models.Website).order_by(models.Website.id.desc()).all()

@app.get("/api/websites/{website_id}", response_model=schemas.WebsiteResponse, tags=["Websites"])
def get_website(website_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Website).filter(models.Website.id == website_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Website not found")
    return item

@app.post("/api/websites", response_model=schemas.WebsiteResponse, status_code=status.HTTP_201_CREATED, tags=["Websites"])
def create_website(item_in: schemas.WebsiteCreate, db: Session = Depends(get_db)):
    new_item = models.Website(**item_in.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.put("/api/websites/{website_id}", response_model=schemas.WebsiteResponse, tags=["Websites"])
def update_website(website_id: int, item_update: schemas.WebsiteUpdate, db: Session = Depends(get_db)):
    item = db.query(models.Website).filter(models.Website.id == website_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Website not found")
    for key, value in item_update.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/websites/{website_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Websites"])
def delete_website(website_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Website).filter(models.Website.id == website_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Website not found")
    db.delete(item)
    db.commit()
    return None

# ==============================================================================
# 4. BLOGS ENDPOINTS (with ML auto-categorization)
# ==============================================================================
@app.get("/api/blogs", response_model=List[schemas.BlogResponse], tags=["Blogs"])
def get_blogs(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Blog)
    if category and category.lower() != "all":
        query = query.filter(models.Blog.category.ilike(f"%{category}%"))
    return query.order_by(models.Blog.id.desc()).all()

@app.get("/api/blogs/{blog_id}", response_model=schemas.BlogResponse, tags=["Blogs"])
def get_blog(blog_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Blog not found")
    return item

@app.post("/api/blogs", response_model=schemas.BlogResponse, status_code=status.HTTP_201_CREATED, tags=["Blogs"])
def create_blog(blog_in: schemas.BlogCreate, db: Session = Depends(get_db)):
    category = blog_in.category
    tags = blog_in.tags

    # Auto-tag and categorize if not set
    if not category or category in ["General", ""]:
        ml_res = ml_engine.categorize_and_tag(blog_in.title, f"{blog_in.summary or ''} {blog_in.content or ''}")
        category = ml_res["category"]
        if not tags:
            tags = ", ".join(ml_res["suggested_tags"])

    new_item = models.Blog(
        title=blog_in.title,
        summary=blog_in.summary,
        content=blog_in.content,
        category=category,
        tags=tags,
        url=blog_in.url,
        image_url=blog_in.image_url
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.put("/api/blogs/{blog_id}", response_model=schemas.BlogResponse, tags=["Blogs"])
def update_blog(blog_id: int, item_update: schemas.BlogUpdate, db: Session = Depends(get_db)):
    item = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Blog not found")
    for key, value in item_update.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/blogs/{blog_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Blogs"])
def delete_blog(blog_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Blog not found")
    db.delete(item)
    db.commit()
    return None

# ==============================================================================
# 5. CERTIFICATIONS ENDPOINTS
# ==============================================================================
@app.get("/api/certifications", response_model=List[schemas.CertificationResponse], tags=["Certifications"])
def get_certifications(db: Session = Depends(get_db)):
    return db.query(models.Certification).order_by(models.Certification.id.desc()).all()

@app.get("/api/certifications/{cert_id}", response_model=schemas.CertificationResponse, tags=["Certifications"])
def get_certification(cert_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Certification).filter(models.Certification.id == cert_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Certification not found")
    return item

@app.post("/api/certifications", response_model=schemas.CertificationResponse, status_code=status.HTTP_201_CREATED, tags=["Certifications"])
def create_certification(item_in: schemas.CertificationCreate, db: Session = Depends(get_db)):
    new_item = models.Certification(**item_in.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.put("/api/certifications/{cert_id}", response_model=schemas.CertificationResponse, tags=["Certifications"])
def update_certification(cert_id: int, item_update: schemas.CertificationUpdate, db: Session = Depends(get_db)):
    item = db.query(models.Certification).filter(models.Certification.id == cert_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Certification not found")
    for key, value in item_update.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/certifications/{cert_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Certifications"])
def delete_certification(cert_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Certification).filter(models.Certification.id == cert_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Certification not found")
    db.delete(item)
    db.commit()
    return None

# ==============================================================================
# 6. COURSES & LICENSES ENDPOINTS
# ==============================================================================
@app.get("/api/courses", response_model=List[schemas.CourseLicenseResponse], tags=["Courses & Licenses"])
def get_courses(db: Session = Depends(get_db)):
    return db.query(models.CourseLicense).order_by(models.CourseLicense.id.desc()).all()

@app.get("/api/courses/{course_id}", response_model=schemas.CourseLicenseResponse, tags=["Courses & Licenses"])
def get_course(course_id: int, db: Session = Depends(get_db)):
    item = db.query(models.CourseLicense).filter(models.CourseLicense.id == course_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")
    return item

@app.post("/api/courses", response_model=schemas.CourseLicenseResponse, status_code=status.HTTP_201_CREATED, tags=["Courses & Licenses"])
def create_course(item_in: schemas.CourseLicenseCreate, db: Session = Depends(get_db)):
    new_item = models.CourseLicense(**item_in.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.put("/api/courses/{course_id}", response_model=schemas.CourseLicenseResponse, tags=["Courses & Licenses"])
def update_course(course_id: int, item_update: schemas.CourseLicenseUpdate, db: Session = Depends(get_db)):
    item = db.query(models.CourseLicense).filter(models.CourseLicense.id == course_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")
    for key, value in item_update.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Courses & Licenses"])
def delete_course(course_id: int, db: Session = Depends(get_db)):
    item = db.query(models.CourseLicense).filter(models.CourseLicense.id == course_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(item)
    db.commit()
    return None

# ==============================================================================
# 7. PHOTOS ENDPOINTS
# ==============================================================================
@app.get("/api/photos", response_model=List[schemas.PhotoResponse], tags=["Photos"])
def get_photos(db: Session = Depends(get_db)):
    return db.query(models.Photo).order_by(models.Photo.id.desc()).all()

@app.get("/api/photos/{photo_id}", response_model=schemas.PhotoResponse, tags=["Photos"])
def get_photo(photo_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Photo).filter(models.Photo.id == photo_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Photo not found")
    return item

@app.post("/api/photos", response_model=schemas.PhotoResponse, status_code=status.HTTP_201_CREATED, tags=["Photos"])
def create_photo(item_in: schemas.PhotoCreate, db: Session = Depends(get_db)):
    new_item = models.Photo(**item_in.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.put("/api/photos/{photo_id}", response_model=schemas.PhotoResponse, tags=["Photos"])
def update_photo(photo_id: int, item_update: schemas.PhotoUpdate, db: Session = Depends(get_db)):
    item = db.query(models.Photo).filter(models.Photo.id == photo_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Photo not found")
    for key, value in item_update.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Photos"])
def delete_photo(photo_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Photo).filter(models.Photo.id == photo_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Photo not found")
    db.delete(item)
    db.commit()
    return None

# ==============================================================================
# 8. LINKS / URLS ENDPOINTS
# ==============================================================================
@app.get("/api/links", response_model=List[schemas.LinkUrlResponse], tags=["Links"])
def get_links(db: Session = Depends(get_db)):
    return db.query(models.LinkUrl).order_by(models.LinkUrl.id.asc()).all()

@app.get("/api/links/{link_id}", response_model=schemas.LinkUrlResponse, tags=["Links"])
def get_link(link_id: int, db: Session = Depends(get_db)):
    item = db.query(models.LinkUrl).filter(models.LinkUrl.id == link_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Link not found")
    return item

@app.post("/api/links", response_model=schemas.LinkUrlResponse, status_code=status.HTTP_201_CREATED, tags=["Links"])
def create_link(item_in: schemas.LinkUrlCreate, db: Session = Depends(get_db)):
    new_item = models.LinkUrl(**item_in.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.put("/api/links/{link_id}", response_model=schemas.LinkUrlResponse, tags=["Links"])
def update_link(link_id: int, item_update: schemas.LinkUrlUpdate, db: Session = Depends(get_db)):
    item = db.query(models.LinkUrl).filter(models.LinkUrl.id == link_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Link not found")
    for key, value in item_update.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Links"])
def delete_link(link_id: int, db: Session = Depends(get_db)):
    item = db.query(models.LinkUrl).filter(models.LinkUrl.id == link_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Link not found")
    db.delete(item)
    db.commit()
    return None

# ==============================================================================
# 9. CONTACT FORM MESSAGES ENDPOINTS
# ==============================================================================
@app.post("/api/contact", response_model=schemas.ContactMessageResponse, status_code=status.HTTP_201_CREATED, tags=["Contact"])
def submit_contact_form(
    msg_in: schemas.ContactMessageCreate
):
    try:
        send_contact_emails(msg_in)
    except Exception as error:
        print(f"Failed to send contact email: {error}")
        raise HTTPException(status_code=503, detail="Email delivery is temporarily unavailable. Please try again later.") from error

    now = datetime.utcnow()
    return schemas.ContactMessageResponse(
        **msg_in.model_dump(),
        id=int(now.timestamp() * 1000),
        status="pending",
        created_at=now,
    )

@app.get("/api/contact", response_model=List[schemas.ContactMessageResponse], tags=["Contact"])
def get_contact_messages():
    return []

@app.patch("/api/contact/{message_id}", response_model=schemas.ContactMessageResponse, tags=["Contact"])
def update_contact_message(
    message_id: int,
    message_update: schemas.ContactMessageUpdate
):
    raise HTTPException(status_code=404, detail="Contact messages are managed in Gmail")

@app.delete("/api/contact/{message_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Contact"])
def delete_contact_message(message_id: int):
    raise HTTPException(status_code=404, detail="Contact messages are managed in Gmail")

# ==============================================================================
# 10. MACHINE LEARNING CATEGORIZATION & TAGGING API
# ==============================================================================
@app.post("/api/ml/categorize", response_model=schemas.MLCategorizeResponse, tags=["Machine Learning"])
def ml_categorize(req: schemas.MLCategorizeRequest):
    """
    NLP Categorization and Auto-Tagging Endpoint.
    Automatically assigns entries to 'Cyber Security', 'Digital Forensics',
    'Web Design', or 'AI/ML' based on text semantics.
    """
    res = ml_engine.categorize_and_tag(
        title=req.title or "",
        description=req.description or "",
        text=req.text or ""
    )
    return schemas.MLCategorizeResponse(
        category=res["category"],
        confidence=res["confidence"],
        suggested_tags=res["suggested_tags"],
        category_scores=res["category_scores"]
    )

# ==============================================================================
# 11. MEDIA UPLOAD ENDPOINT
# ==============================================================================
@app.post("/api/upload", tags=["Media"])
def upload_file(file: UploadFile = File(...)):
    raise HTTPException(status_code=503, detail="Media storage is disabled")


@app.get("/api/media/{file_id}", tags=["Media"])
def serve_drive_media(file_id: str):
    raise HTTPException(status_code=404, detail="Media storage is disabled")

# ============================================================================== 
# Frontend Files
# ============================================================================== 
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/", include_in_schema=False)
def serve_portfolio():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/main.js", include_in_schema=False)
def serve_main_script():
    return FileResponse(os.path.join(FRONTEND_DIR, "main.js"), media_type="text/javascript")

@app.get("/admin.html", include_in_schema=False)
def serve_admin_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))

@app.get("/colored-logo.png", include_in_schema=False)
def serve_logo():
    return FileResponse(os.path.join(FRONTEND_DIR, "colored-logo.png"), media_type="image/png")

if __name__ == "__main__":
    import socket
    import uvicorn

    port = 8001
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            port = 8002
            print("Port 8001 is already in use; starting the server on port 8002.")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
