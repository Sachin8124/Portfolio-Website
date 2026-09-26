/**
 * Sachin Burman Portfolio - Dynamic Frontend Engine (main.js)
 * Connects index.html to the FastAPI backend + ML services.
 */

const DEFAULT_BACKEND = window.location.protocol === "file:"
    ? "http://127.0.0.1:8001"
    : window.location.origin;
const API_BASE = `${window.PORTFOLIO_API_BASE || DEFAULT_BACKEND}/api`;
const MEDIA_BASE = window.PORTFOLIO_MEDIA_BASE || DEFAULT_BACKEND;

let projectsData = [];
let skillsData = [];
let certificationsData = [];
let blogsData = [];
let activeCategoryFilter = "all";
let searchDebounceTimer = null;

const PROFILE_STORAGE_KEY = "sachin_portfolio_profile";

function resolveMediaUrl(url) {
    if (!url) return "";
    return url.startsWith("http") ? url : `${MEDIA_BASE}${url}`;
}

function resolveExternalUrl(url) {
    if (!url) return "";
    return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

function loadSavedProfile() {
    try {
        const profile = JSON.parse(localStorage.getItem(PROFILE_STORAGE_KEY) || "{}");
        if (Array.isArray(profile.heroRoles) && profile.heroRoles.join("|") === "Web Developer|UI Designer|Cyber Security Enthusiast") {
            profile.heroRoles = ["Cyber Security Enthusiast", "Web Developer"];
            localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
        }
        return profile;
    } catch {
        return {};
    }
}

function applySavedProfile() {
    const profile = loadSavedProfile();
    const brandName = document.getElementById("siteBrandName");
    const heroName = document.getElementById("heroName");
    const aboutImage = document.getElementById("aboutImage");
    const aboutTitle = document.getElementById("aboutTitle");
    const aboutDescription = document.getElementById("aboutDescription");
    const heroWelcomeText = document.getElementById("heroWelcomeText");

    if (brandName && profile.brandName) brandName.textContent = profile.brandName;
    if (heroName && profile.fullName) heroName.textContent = profile.fullName;
    if (aboutImage && profile.logoUrl) aboutImage.src = profile.logoUrl;
    if (aboutTitle && profile.aboutTitle) aboutTitle.textContent = profile.aboutTitle;
    if (aboutDescription && profile.aboutDescription) aboutDescription.textContent = profile.aboutDescription;
    if (heroWelcomeText && profile.heroWelcomeText) heroWelcomeText.textContent = profile.heroWelcomeText;
}

// ==============================================================================
// Toast Notification Helper
// ==============================================================================
function showToast(message, isError = false) {
    const toast = document.getElementById("toast");
    if (!toast) return;

    toast.textContent = message;
    toast.style.backgroundColor = isError ? "#ef4444" : "var(--accent, #38bdf8)";
    toast.style.color = isError ? "#ffffff" : "#0f172a";
    toast.style.fontWeight = "600";
    toast.className = "show";

    setTimeout(() => {
        toast.className = toast.className.replace("show", "");
    }, 3500);
}

function getApiErrorMessage(errorData, fallback) {
    const detail = errorData && errorData.detail;
    if (Array.isArray(detail)) {
        const messages = detail
            .map(error => error && error.msg)
            .filter(Boolean);
        if (messages.length) return messages.join(" ");
    }
    if (typeof detail === "string" && detail.trim()) return detail;
    if (detail && typeof detail === "object") {
        try {
            return JSON.stringify(detail);
        } catch {
            return fallback;
        }
    }
    return fallback;
}

// ==============================================================================
// 1. Fetch & Render Projects
// ==============================================================================
async function loadProjects() {
    const container = document.getElementById("dynamic-projects-container") || document.querySelector(".portfolio-container");
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE}/projects`);
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        
        projectsData = await response.json();
        renderProjects(projectsData);
    } catch (err) {
        console.warn("Backend API not reachable. Retaining fallback content.", err);
    }
}

function renderProjects(items) {
    const container = document.getElementById("dynamic-projects-container") || document.querySelector(".portfolio-container");
    if (!container) return;
    let filtered = items;
    if (activeCategoryFilter !== "all") {
        filtered = items.filter(p => p.category && p.category.toLowerCase().includes(activeCategoryFilter.toLowerCase()));
    }

    const searchInput = document.getElementById("semanticSearchInput");
    if (searchInput && searchInput.value.trim()) {
        const q = searchInput.value.trim().toLowerCase();
        filtered = filtered.filter(p => 
            (p.title && p.title.toLowerCase().includes(q)) ||
            (p.description && p.description.toLowerCase().includes(q)) ||
            (p.tags && p.tags.toLowerCase().includes(q)) ||
            (p.category && p.category.toLowerCase().includes(q))
        );
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px 20px; color: var(--text-secondary);">
                <i class="fa-solid fa-magnifying-glass" style="font-size: 2.5rem; color: var(--accent); margin-bottom: 15px; opacity: 0.7;"></i>
                <p>No projects found matching the selected filter.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map(item => {
        const hasImg = item.image_url && item.image_url.trim() !== "";
        const imgSrc = hasImg 
            ? (item.image_url.startsWith("http") ? item.image_url : `${MEDIA_BASE}${item.image_url}`)
            : null;

        let defaultIcon = "fa-solid fa-laptop-code";
        const cat = (item.category || "").toLowerCase();
        if (cat.includes("security")) defaultIcon = "fa-solid fa-shield-halved";
        else if (cat.includes("forensic")) defaultIcon = "fa-solid fa-fingerprint";
        else if (cat.includes("design") || cat.includes("ui")) defaultIcon = "fa-solid fa-palette";
        else if (cat.includes("ai") || cat.includes("ml")) defaultIcon = "fa-solid fa-brain";

        // Parse tags
        let tagsHtml = "";
        if (item.tags) {
            const tagArray = item.tags.split(",").map(t => t.trim()).filter(Boolean);
            if (tagArray.length > 0) {
                tagsHtml = `<div class="tags-container" style="display:flex; flex-wrap:wrap; gap:6px; margin: 10px 0 15px 0;">
                    ${tagArray.map(t => `<span class="tag-chip" style="background: rgba(56,189,248,0.1); color: var(--accent); border: 1px solid rgba(56,189,248,0.3); border-radius: 12px; padding: 3px 10px; font-size: 0.75rem; font-weight: 500;">${escapeHtml(t)}</span>`).join("")}
                </div>`;
            }
        }

        const externalLink = item.external_url 
            ? `<a href="${escapeHtml(item.external_url)}" target="_blank" rel="noopener noreferrer" title="View Project"><i class="fa-solid fa-up-right-from-square"></i></a>`
            : `<a href="#contact" title="Contact Me"><i class="fa-solid fa-arrow-right"></i></a>`;

        return `
            <div class="portfolio-box">
                <div class="portfolio-img">
                    ${imgSrc 
                        ? `<img src="${imgSrc}" alt="${escapeHtml(item.title)}" style="width:100%;height:100%;object-fit:cover;">`
                        : `<i class="${defaultIcon}"></i>`}
                </div>
                <div class="portfolio-layer">
                    <span style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: var(--accent); font-weight: 600; display:block; margin-bottom: 5px;">
                        ${escapeHtml(item.category || "Project")}
                    </span>
                    <h4>${escapeHtml(item.title)}</h4>
                    <p>${escapeHtml(item.description || "")}</p>
                    ${tagsHtml}
                    ${externalLink}
                </div>
            </div>
        `;
    }).join("");
}

// ==============================================================================
// 2. Fetch & Render Blog Articles
// ============================================================================
async function loadBlogs() {
    const container = document.getElementById("dynamic-blogs-container");
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE}/blogs`);
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        blogsData = await response.json();
        renderBlogs(blogsData);
    } catch (err) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">Articles are temporarily unavailable.</div>`;
        console.warn("Could not load blogs from backend.", err);
    }
}

function renderBlogs(items) {
    const container = document.getElementById("dynamic-blogs-container");
    if (!container) return;
    if (!items.length) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:18px; color:var(--text-secondary);">New articles will appear here soon.</div>`;
        return;
    }

    container.innerHTML = items.map(blog => {
        const tags = (blog.tags || "").split(",").map(tag => tag.trim()).filter(Boolean);
        const articleUrl = resolveExternalUrl(blog.url);
        return `
            <article class="blog-card">
                <div class="blog-card-meta">
                    <span><i class="fa-solid fa-layer-group"></i> ${escapeHtml(blog.category || "Article")}</span>
                    <i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i>
                </div>
                <h4>${escapeHtml(blog.title)}</h4>
                <p class="blog-card-summary">${escapeHtml(blog.summary || blog.content || "Explore this article from my portfolio.")}</p>
                ${tags.length ? `<div class="blog-tags">${tags.map(tag => `<span class="blog-tag">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
                ${articleUrl ? `<a class="blog-card-link" href="${escapeHtml(articleUrl)}" target="_blank" rel="noopener noreferrer">Read article <i class="fa-solid fa-arrow-right"></i></a>` : `<span class="blog-card-link" style="color:var(--text-secondary);">Article details <i class="fa-solid fa-arrow-right"></i></span>`}
            </article>
        `;
    }).join("");
}

// ============================================================================
// 3. Fetch & Render Skills
// ==============================================================================
async function loadSkills() {
    const container = document.getElementById("dynamic-skills-container") || document.querySelector(".skills-container");
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE}/skills`);
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);

        skillsData = await response.json();
        renderSkills(skillsData);
    } catch (err) {
        console.warn("Could not load skills from backend. Preserving fallback skills.", err);
    }
}

function renderSkills(items) {
    const container = document.getElementById("dynamic-skills-container") || document.querySelector(".skills-container");
    if (!container || !items || items.length === 0) return;

    container.innerHTML = items.map(skill => `
        <div class="skill-card">
            <i class="${skill.icon || 'fa-solid fa-code'}"></i>
            <h3>${escapeHtml(skill.name)}</h3>
            ${skill.proficiency ? `<span style="font-size:0.8rem; color: var(--text-secondary); display:block; margin-top:4px;">${escapeHtml(skill.proficiency)}</span>` : ""}
        </div>
    `).join("");
}

async function loadCourses() {
    const container = document.getElementById("dynamic-courses-container");
    if (!container) return;
    try {
        const response = await fetch(`${API_BASE}/courses`);
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        renderCourses(await response.json());
    } catch (err) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">Courses and licenses are temporarily unavailable.</div>`;
        console.warn("Could not load courses from backend.", err);
    }
}

function renderCourses(items) {
    const container = document.getElementById("dynamic-courses-container");
    if (!container) return;
    if (!items.length) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">New courses and licenses will appear here soon.</div>`;
        return;
    }
    container.innerHTML = items.map(course => `
        <article class="resource-card">
            <div class="resource-card-icon"><i class="fa-solid fa-graduation-cap"></i></div>
            <h3>${escapeHtml(course.title)}</h3>
            <p class="resource-meta">${escapeHtml(course.institution)}</p>
            ${course.license_number ? `<p style="margin-top:8px;">License / ID: ${escapeHtml(course.license_number)}</p>` : ""}
            ${course.credential_url ? `<a class="resource-action" href="${escapeHtml(resolveExternalUrl(course.credential_url))}" target="_blank" rel="noopener noreferrer">View credential <i class="fa-solid fa-arrow-up-right-from-square"></i></a>` : ""}
        </article>
    `).join("");
}

async function loadWebsites() {
    const container = document.getElementById("dynamic-websites-container");
    if (!container) return;
    try {
        const response = await fetch(`${API_BASE}/websites`);
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        renderWebsites(await response.json());
    } catch (err) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">Websites are temporarily unavailable.</div>`;
        console.warn("Could not load websites from backend.", err);
    }
}

function renderWebsites(items) {
    const container = document.getElementById("dynamic-websites-container");
    if (!container) return;
    if (!items.length) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">Featured websites will appear here soon.</div>`;
        return;
    }
    container.innerHTML = items.map(website => `
        <article class="resource-card">
            <div class="resource-card-icon"><i class="fa-solid fa-globe"></i></div>
            <h3>${escapeHtml(website.title)}</h3>
            <p>${escapeHtml(website.description || "Explore this website and its digital experience.")}</p>
            <a class="resource-action" href="${escapeHtml(resolveExternalUrl(website.url))}" target="_blank" rel="noopener noreferrer">Visit website <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
        </article>
    `).join("");
}

async function loadPhotos() {
    const container = document.getElementById("dynamic-photos-container");
    if (!container) return;
    try {
        const response = await fetch(`${API_BASE}/photos`);
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        renderPhotos(await response.json());
    } catch (err) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">Photos are temporarily unavailable.</div>`;
        console.warn("Could not load photos from backend.", err);
    }
}

function renderPhotos(items) {
    const container = document.getElementById("dynamic-photos-container");
    if (!container) return;
    if (!items.length) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">Photos will appear here as they are added.</div>`;
        return;
    }
    container.innerHTML = items.map(photo => {
        const imageUrl = resolveMediaUrl(photo.image_url);
        return `
            <article class="photo-card">
                <a href="${escapeHtml(imageUrl)}" target="_blank" rel="noopener noreferrer" aria-label="Open ${escapeHtml(photo.title)}">
                    <img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(photo.title)}" loading="lazy">
                </a>
                <div class="photo-card-content">
                    <h3>${escapeHtml(photo.title)}</h3>
                    ${photo.caption ? `<p>${escapeHtml(photo.caption)}</p>` : ""}
                </div>
            </article>
        `;
    }).join("");
}

// ============================================================================
// 3. Fetch & Render Certifications
// ============================================================================
async function loadCertifications() {
    const container = document.getElementById("dynamic-certifications-container");
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE}/certifications`);
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        certificationsData = await response.json();
        renderCertifications(certificationsData);
    } catch (err) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">Certifications are temporarily unavailable.</div>`;
        console.warn("Could not load certifications from backend.", err);
    }
}

function renderCertifications(items) {
    const container = document.getElementById("dynamic-certifications-container");
    if (!container) return;
    if (!items.length) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; color:var(--text-secondary);">New certifications will appear here soon.</div>`;
        return;
    }

    container.innerHTML = items.map(certification => {
        const assetUrl = resolveMediaUrl(certification.image_url);
        const isPdf = /\.pdf(?:$|\?)/i.test(assetUrl) || /[?&]type=pdf(?:&|$)/i.test(assetUrl);
        const credentialUrl = certification.credential_url ? escapeHtml(certification.credential_url) : "";
        return `
            <article class="certification-card">
                ${assetUrl && !isPdf ? `<img class="certification-preview" src="${escapeHtml(assetUrl)}" alt="${escapeHtml(certification.title)} certificate">` : `<div class="certification-icon"><i class="fa-solid ${isPdf ? "fa-file-pdf" : "fa-certificate"}"></i></div>`}
                <h3>${escapeHtml(certification.title)}</h3>
                <p class="certification-issuer">${escapeHtml(certification.issuer)}</p>
                ${certification.issue_date ? `<p class="certification-date"><i class="fa-regular fa-calendar"></i> ${escapeHtml(certification.issue_date)}</p>` : ""}
                <div class="certification-actions">
                    ${assetUrl ? `<a href="${escapeHtml(assetUrl)}" target="_blank" rel="noopener noreferrer"><i class="fa-solid ${isPdf ? "fa-file-pdf" : "fa-image"}"></i> ${isPdf ? "View PDF" : "View Certificate"}</a>` : ""}
                    ${credentialUrl ? `<a href="${credentialUrl}" target="_blank" rel="noopener noreferrer"><i class="fa-solid fa-arrow-up-right-from-square"></i> Verify Credential</a>` : ""}
                </div>
            </article>
        `;
    }).join("");
}

// ==============================================================================
// 3. Contact Form Submission (Asynchronous POST to FastAPI)
// ==============================================================================
function initContactForm() {
    const form = document.getElementById("contactForm") || document.querySelector(".contact form");
    if (!form) return;

    form.addEventListener("submit", async function(e) {
        e.preventDefault();

        // Extract form values
        const inputs = form.querySelectorAll("input");
        const textarea = form.querySelector("textarea");

        let fullName = "";
        let email = "";
        let mobile = "";
        let subject = "";
        let message = textarea ? textarea.value.trim() : "";

        inputs.forEach(input => {
            const type = (input.getAttribute("type") || "").toLowerCase();
            const placeholder = (input.getAttribute("placeholder") || "").toLowerCase();

            if (type === "email") {
                email = input.value.trim();
            } else if (placeholder.includes("subject")) {
                subject = input.value.trim();
            } else if (type === "number" || placeholder.includes("mobile") || placeholder.includes("phone")) {
                mobile = input.value.trim();
            } else if (type === "text" && !fullName) {
                fullName = input.value.trim();
            }
        });

        if (!fullName || !email || !message) {
            showToast("Please fill in your name, email, and message.", true);
            return;
        }

        const submitBtn = form.querySelector('input[type="submit"]') || form.querySelector("button[type='submit']");
        const originalBtnVal = submitBtn ? submitBtn.value : "Send Message";
        if (submitBtn) {
            submitBtn.value = "Sending...";
            submitBtn.disabled = true;
        }

        try {
            const response = await fetch(`${API_BASE}/contact`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    full_name: fullName,
                    email: email,
                    mobile: mobile,
                    subject: subject,
                    message: message
                })
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(getApiErrorMessage(errData, "Failed to deliver message"));
            }

            // Success feedback
            showToast("Message Sent Successfully!");
            form.reset();
        } catch (err) {
            console.error("Contact form error:", err);
            showToast(err.message || "Could not send your message. Please try again.", true);
        } finally {
            if (submitBtn) {
                submitBtn.value = originalBtnVal;
                submitBtn.disabled = false;
            }
        }
    });
}

// ==============================================================================
// 4. Project Filters & Search Listeners
// ==============================================================================
function initFilterAndSearch() {
    const searchInput = document.getElementById("semanticSearchInput");
    const clearBtn = document.getElementById("clearSearchBtn");

    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            if (clearBtn) {
                clearBtn.style.display = e.target.value ? "block" : "none";
            }
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(() => {
                renderProjects(projectsData);
            }, 250);
        });
    }

    if (clearBtn && searchInput) {
        clearBtn.addEventListener("click", () => {
            searchInput.value = "";
            clearBtn.style.display = "none";
            renderProjects(projectsData);
        });
    }

    const filterPills = document.querySelectorAll(".filter-pill");
    filterPills.forEach(pill => {
        pill.addEventListener("click", () => {
            filterPills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            activeCategoryFilter = pill.getAttribute("data-filter") || "all";
            renderProjects(projectsData);
        });
    });
}

// ==============================================================================
// 5. Navigation, Typing Animation & Utilities
// ==============================================================================
function initUIEffects() {
    // Mobile navigation toggle
    const menuIcon = document.querySelector('#menu-icon');
    const navbar = document.querySelector('.nav-links');

    if (menuIcon && navbar) {
        menuIcon.onclick = () => {
            menuIcon.classList.toggle('fa-xmark');
            navbar.classList.toggle('active');
        };

        const navLinks = document.querySelectorAll('header nav a');
        navLinks.forEach(link => {
            link.onclick = () => {
                menuIcon.classList.remove('fa-xmark');
                navbar.classList.remove('active');
            };
        });
    }

    // Scroll active link highlight
    const sections = document.querySelectorAll('section');
    const navLinks = document.querySelectorAll('header nav a');
    window.addEventListener('scroll', () => {
        const top = window.scrollY;
        sections.forEach(sec => {
            const offset = sec.offsetTop - 150;
            const height = sec.offsetHeight;
            const id = sec.getAttribute('id');

            if (top >= offset && top < offset + height) {
                navLinks.forEach(links => {
                    links.classList.remove('active');
                    const target = document.querySelector('header nav a[href*=' + id + ']');
                    if (target) target.classList.add('active');
                });
            }
        });

        const header = document.querySelector('header');
        if (header) {
            header.classList.toggle('sticky', window.scrollY > 100);
        }
    });

    // Typing effect
    const textElement = document.getElementById('typing-text');
    if (textElement) {
        const savedProfile = loadSavedProfile();
        const texts = Array.isArray(savedProfile.heroRoles) && savedProfile.heroRoles.length
            ? savedProfile.heroRoles
            : ["Cyber Security Enthusiast", "Web Developer"];
        let count = 0;
        let index = 0;
        let currentText = '';
        let letter = '';

        (function type() {
            if (count === texts.length) count = 0;
            currentText = texts[count];
            letter = currentText.slice(0, ++index);
            textElement.textContent = letter;

            if (letter.length === currentText.length) {
                count++;
                index = 0;
                setTimeout(type, 2000);
            } else {
                setTimeout(type, 100);
            }
        })();
    }

    const imageTrigger = document.getElementById("aboutImageTrigger");
    const imageViewer = document.getElementById("imageViewer");
    const imageViewerImage = document.getElementById("imageViewerImage");
    const imageViewerClose = document.getElementById("imageViewerClose");

    if (imageTrigger && imageViewer && imageViewerImage && imageViewerClose) {
        const closeImageViewer = () => {
            imageViewer.classList.remove("active");
            imageViewer.setAttribute("aria-hidden", "true");
            document.body.style.overflow = "";
        };

        const openImageViewer = () => {
            const sourceImage = document.getElementById("aboutImage");
            imageViewerImage.src = sourceImage ? sourceImage.src : "";
            imageViewerImage.alt = sourceImage ? sourceImage.alt : "Profile image";
            imageViewer.classList.add("active");
            imageViewer.setAttribute("aria-hidden", "false");
            document.body.style.overflow = "hidden";
            imageViewerClose.focus();
        };

        imageTrigger.addEventListener("click", openImageViewer);
        imageTrigger.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openImageViewer();
            }
        });
        imageViewerClose.addEventListener("click", closeImageViewer);
        imageViewer.addEventListener("click", event => {
            if (event.target === imageViewer) closeImageViewer();
        });
        document.addEventListener("keydown", event => {
            if (event.key === "Escape" && imageViewer.classList.contains("active")) closeImageViewer();
        });
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
    applySavedProfile();
    initUIEffects();
    initContactForm();
    initFilterAndSearch();
    loadProjects();
    loadBlogs();
    loadSkills();
    loadCertifications();
    loadCourses();
    loadWebsites();
    loadPhotos();
});
