import re
from typing import List, Dict, Tuple

TRAINING_CORPUS = [
    # --- Cyber Security ---
    ("SE-GUARD platform for automated threat detection vulnerability scanner and network defense", "Cyber Security"),
    ("Penetration testing ethical hacking exploit analysis and security audit of web applications", "Cyber Security"),
    ("Network firewall intrusion detection system IDS IPS security monitoring and packet filtering", "Cyber Security"),
    ("Vulnerability assessment scanning OWASP Top 10 exploits patch management and defense", "Cyber Security"),
    ("Malware analysis reverse engineering Trojan detection ransomware mitigation and sandbox testing", "Cyber Security"),
    ("Cryptography encryption hashing protocols SSL TLS certificate management and key exchange", "Cyber Security"),
    ("SOC monitoring incident response security operations threat intelligence and SIEM integration", "Cyber Security"),
    ("Active Directory privilege escalation kerberoasting defense and credential theft mitigation", "Cyber Security"),
    ("Zero-day exploit mitigation network traffic anomaly analysis and threat hunting", "Cyber Security"),

    # --- Digital Forensics ---
    ("Cyber forensics report investigation digital evidence extraction and chain of custody documentation", "Digital Forensics"),
    ("Memory forensics RAM dump analysis using Volatility framework process injection detection", "Digital Forensics"),
    ("Autopsy disk forensics file carving unallocated clusters deleted file recovery partition table", "Digital Forensics"),
    ("Network forensics packet capture PCAP Wireshark traffic reconstruction and anomaly tracking", "Digital Forensics"),
    ("Windows registry forensics user activity logs Prefetch shimcache event viewer artifact extraction", "Digital Forensics"),
    ("Mobile device forensics Android iOS SQLite database forensic acquisition and timeline synthesis", "Digital Forensics"),
    ("Disk imaging bit-stream backup forensic duplication hash verification SHA256 integrity check", "Digital Forensics"),
    ("Browser history cache cookies session carving digital trail reconstruction forensic investigator", "Digital Forensics"),

    # --- Web Design ---
    ("Food delivering UI layout responsive web design built with Adobe XD visual component system", "Web Design"),
    ("Food ordering UI interactive PizzaHut layout designed in Figma with custom components and micro-interactions", "Web Design"),
    ("Modern personal portfolio website responsive HTML5 CSS3 JavaScript mobile-first UX", "Web Design"),
    ("Figma prototyping wireframing design system typography color palette user interface UI UX", "Web Design"),
    ("Responsive navigation layout card grid flexbox CSS animations transitions accessible design", "Web Design"),
    ("Landing page design conversion rate optimization hero section call to action dark mode theme", "Web Design"),
    ("Design thinking user research persona empathy mapping journey map usability testing prototype", "Web Design"),
    ("Front-end design web development CSS grid glassmorphism dashboard UI client showcase", "Web Design"),

    # --- AI/ML ---
    ("Machine learning pipeline NLP classification transformer embeddings scikit-learn PyTorch", "AI/ML"),
    ("Deep neural network training computer vision CNN object detection image classification", "AI/ML"),
    ("Natural language processing text sentiment analysis TF-IDF vectorizer tokenization BERT", "AI/ML"),
    ("Predictive analytics regression classification clustering unsupervised learning data science", "AI/ML"),
    ("Large language models LLM prompt engineering vector database RAG generative AI agents", "AI/ML"),
    ("Model evaluation cross-validation ROC AUC precision recall metrics hyperparameter tuning", "AI/ML"),
    ("Feature engineering data cleaning normalization exploratory data analysis pandas numpy", "AI/ML"),
]

DOMAIN_TAGS = {
    "Cyber Security": [
        "Cyber Security", "SE-GUARD", "Penetration Testing", "Ethical Hacking", "Vulnerability Assessment",
        "Network Defense", "Threat Intelligence", "OWASP", "Firewall", "Malware Analysis",
        "Cryptography", "SIEM", "Incident Response", "SOC"
    ],
    "Digital Forensics": [
        "Digital Forensics", "Cyber Forensics", "Evidence Analysis", "Memory Forensics", "Volatility",
        "Autopsy", "Disk Forensics", "Packet Capture", "Wireshark", "Chain of Custody",
        "Artifact Extraction", "Registry Forensics", "Timeline Analysis"
    ],
    "Web Design": [
        "UI/UX Design", "Web Design", "Figma", "Adobe XD", "Responsive UI",
        "Prototyping", "HTML5/CSS3", "Frontend", "Wireframing", "Design System",
        "User Experience", "Mobile First", "Component Architecture"
    ],
    "AI/ML": [
        "AI/ML", "Machine Learning", "NLP", "Scikit-Learn", "Deep Learning",
        "Neural Networks", "Data Science", "Text Classification", "Predictive Analytics",
        "Computer Vision", "Model Deployment"
    ]
}

class PortfolioMLCategorizer:
    def __init__(self):
        self.is_trained = False
        self.vectorizer = None
        self.model = None
        self._init_model()

    def _init_model(self):
        """Train the scikit-learn TF-IDF + LogisticRegression model on domain data."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression

            texts = [item[0] for item in TRAINING_CORPUS]
            labels = [item[1] for item in TRAINING_CORPUS]

            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
                lowercase=True,
                token_pattern=r"(?u)\b\w[\w-]+\b"
            )
            X = self.vectorizer.fit_transform(texts)

            # Use lbfgs solver for multiclass support
            self.model = LogisticRegression(C=5.0, solver="lbfgs", max_iter=200, random_state=42)
            self.model.fit(X, labels)
            self.is_trained = True
        except Exception as err:
            self.is_trained = False

    def predict(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        """Predict the portfolio category with confidence scores."""
        if not text or not text.strip():
            return "General", 0.5, {"General": 0.5}

        if self.is_trained and self.model and self.vectorizer:
            try:
                vec = self.vectorizer.transform([text])
                probs = self.model.predict_proba(vec)[0]
                classes = self.model.classes_
                scores = {str(cls_name): round(float(prob), 4) for cls_name, prob in zip(classes, probs)}
                best_idx = probs.argmax()
                best_class = str(classes[best_idx])
                best_conf = round(float(probs[best_idx]), 4)
                return best_class, best_conf, scores
            except Exception:
                pass

        # Fallback keyword scoring
        lower_text = text.lower()
        keyword_scores = {
            "Cyber Security": 0,
            "Digital Forensics": 0,
            "Web Design": 0,
            "AI/ML": 0,
        }

        keywords = {
            "Cyber Security": ["security", "se-guard", "penetration", "hack", "vulnerability", "exploit", "threat", "firewall", "malware", "crypto"],
            "Digital Forensics": ["forensic", "evidence", "memory", "volatility", "autopsy", "disk", "chain of custody", "artifact", "wireshark", "pcap"],
            "Web Design": ["ui", "ux", "design", "figma", "adobe", "xd", "css", "html", "web", "layout", "responsive", "frontend", "prototype"],
            "AI/ML": ["machine learning", "ml", "ai", "nlp", "neural", "deep learning", "model", "scikit", "prediction", "data science"]
        }

        for cat, kw_list in keywords.items():
            for kw in kw_list:
                if kw in lower_text:
                    keyword_scores[cat] += 1

        best_cat = max(keyword_scores, key=keyword_scores.get)
        total = sum(keyword_scores.values()) or 1
        conf = round(max(0.5, keyword_scores[best_cat] / total), 4)
        prob_dict = {k: round(v / total, 4) for k, v in keyword_scores.items()}
        return best_cat, conf, prob_dict

    def extract_tags(self, text: str, category: str, max_tags: int = 5) -> List[str]:
        """Extract relevant technical tags based on matched domain keywords and content."""
        tags = []
        lower_text = text.lower()

        if category not in tags and category != "General":
            tags.append(category)

        domain_list = DOMAIN_TAGS.get(category, [])
        for candidate in domain_list:
            pattern = r"\b" + re.escape(candidate.lower()) + r"\b"
            if re.search(pattern, lower_text) and candidate not in tags:
                tags.append(candidate)
            if len(tags) >= max_tags:
                break

        if len(tags) < max_tags:
            for cat, c_list in DOMAIN_TAGS.items():
                if cat == category:
                    continue
                for candidate in c_list:
                    pattern = r"\b" + re.escape(candidate.lower()) + r"\b"
                    if re.search(pattern, lower_text) and candidate not in tags:
                        tags.append(candidate)
                    if len(tags) >= max_tags:
                        break
                if len(tags) >= max_tags:
                    break

        if len(tags) < 2 and category in DOMAIN_TAGS:
            for fallback_tag in DOMAIN_TAGS[category][:3]:
                if fallback_tag not in tags:
                    tags.append(fallback_tag)
                if len(tags) >= 3:
                    break

        return tags[:max_tags]

    def categorize_and_tag(self, title: str = "", description: str = "", text: str = "") -> Dict:
        """Full pipeline: classify text into category and generate suggested tags."""
        combined_text = f"{title} {description} {text}".strip()
        category, confidence, scores = self.predict(combined_text)
        suggested_tags = self.extract_tags(combined_text, category)

        return {
            "category": category,
            "confidence": confidence,
            "suggested_tags": suggested_tags,
            "category_scores": scores
        }

ml_engine = PortfolioMLCategorizer()
