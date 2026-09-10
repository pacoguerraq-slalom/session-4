"""
Slalom Capabilities Management System API

A FastAPI application that enables Slalom consultants to register their
capabilities and manage consulting expertise across the organization.
"""

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Slalom Capabilities Management API",
              description="API for managing consulting capabilities and consultant expertise")

security = HTTPBearer(auto_error=False)
sessions = {}
audit_log = []

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


def load_users():
    with (current_dir / "practice_leads.json").open(encoding="utf-8") as users_file:
        return json.load(users_file)


def verify_password(password, user):
    if user.get("password_algorithm") != "pbkdf2_sha256":
        return False

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(user["password_salt"]),
        user.get("password_iterations", 600000),
    ).hex()
    return hmac.compare_digest(password_hash, user["password_hash"])


def record_audit_event(username, action, capability=None):
    audit_log.append({
        "username": username,
        "action": action,
        "capability": capability,
    })


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authentication required")

    username = sessions.get(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired session")

    user = next((item for item in load_users() if item["username"] == username), None)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="User account not found")
    return user


def require_practice_lead(user=Depends(get_current_user)):
    if user.get("role") != "practice_lead":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Practice lead permission required")
    return user


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
def login(request: LoginRequest):
    user = next((item for item in load_users()
                 if item["username"] == request.username), None)
    if user is None or not verify_password(request.password, user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    sessions[token] = user["username"]
    record_audit_event(user["username"], "login")
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
    }


@app.post("/auth/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security),
           user=Depends(get_current_user)):
    sessions.pop(credentials.credentials, None)
    record_audit_event(user["username"], "logout")
    return {"message": "Logged out"}


@app.get("/auth/me")
def get_current_user_profile(user=Depends(get_current_user)):
    return {
        "username": user["username"],
        "role": user["role"],
        "practice_area": user.get("practice_area"),
    }


@app.get("/audit-log")
def get_audit_log(user=Depends(require_practice_lead)):
    return audit_log

# In-memory capabilities database
capabilities = {
    "Cloud Architecture": {
        "description": "Design and implement scalable cloud solutions using AWS, Azure, and GCP",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["AWS Solutions Architect", "Azure Architect Expert"],
        "industry_verticals": ["Healthcare", "Financial Services", "Retail"],
        "capacity": 40,  # hours per week available across team
        "consultants": ["alice.smith@slalom.com", "bob.johnson@slalom.com"]
    },
    "Data Analytics": {
        "description": "Advanced data analysis, visualization, and machine learning solutions",
        "practice_area": "Technology", 
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Tableau Desktop Specialist", "Power BI Expert", "Google Analytics"],
        "industry_verticals": ["Retail", "Healthcare", "Manufacturing"],
        "capacity": 35,
        "consultants": ["emma.davis@slalom.com", "sophia.wilson@slalom.com"]
    },
    "DevOps Engineering": {
        "description": "CI/CD pipeline design, infrastructure automation, and containerization",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"], 
        "certifications": ["Docker Certified Associate", "Kubernetes Admin", "Jenkins Certified"],
        "industry_verticals": ["Technology", "Financial Services"],
        "capacity": 30,
        "consultants": ["john.brown@slalom.com", "olivia.taylor@slalom.com"]
    },
    "Digital Strategy": {
        "description": "Digital transformation planning and strategic technology roadmaps",
        "practice_area": "Strategy",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Digital Transformation Certificate", "Agile Certified Practitioner"],
        "industry_verticals": ["Healthcare", "Financial Services", "Government"],
        "capacity": 25,
        "consultants": ["liam.anderson@slalom.com", "noah.martinez@slalom.com"]
    },
    "Change Management": {
        "description": "Organizational change leadership and adoption strategies",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Prosci Certified", "Lean Six Sigma Black Belt"],
        "industry_verticals": ["Healthcare", "Manufacturing", "Government"],
        "capacity": 20,
        "consultants": ["ava.garcia@slalom.com", "mia.rodriguez@slalom.com"]
    },
    "UX/UI Design": {
        "description": "User experience design and digital product innovation",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Adobe Certified Expert", "Google UX Design Certificate"],
        "industry_verticals": ["Retail", "Healthcare", "Technology"],
        "capacity": 30,
        "consultants": ["amelia.lee@slalom.com", "harper.white@slalom.com"]
    },
    "Cybersecurity": {
        "description": "Information security strategy, risk assessment, and compliance",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["CISSP", "CISM", "CompTIA Security+"],
        "industry_verticals": ["Financial Services", "Healthcare", "Government"],
        "capacity": 25,
        "consultants": ["ella.clark@slalom.com", "scarlett.lewis@slalom.com"]
    },
    "Business Intelligence": {
        "description": "Enterprise reporting, data warehousing, and business analytics",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Microsoft BI Certification", "Qlik Sense Certified"],
        "industry_verticals": ["Retail", "Manufacturing", "Financial Services"],
        "capacity": 35,
        "consultants": ["james.walker@slalom.com", "benjamin.hall@slalom.com"]
    },
    "Agile Coaching": {
        "description": "Agile transformation and team coaching for scaled delivery",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Certified Scrum Master", "SAFe Agilist", "ICAgile Certified"],
        "industry_verticals": ["Technology", "Financial Services", "Healthcare"],
        "capacity": 20,
        "consultants": ["charlotte.young@slalom.com", "henry.king@slalom.com"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/capabilities")
def get_capabilities():
    return capabilities


@app.post("/capabilities/{capability_name}/register")
def register_for_capability(capability_name: str, email: str,
                            user=Depends(require_practice_lead)):
    """Register a consultant for a capability"""
    # Validate capability exists
    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    # Get the specific capability
    capability = capabilities[capability_name]

    # Validate consultant is not already registered
    if email in capability["consultants"]:
        raise HTTPException(
            status_code=400,
            detail="Consultant is already registered for this capability"
        )

    # Add consultant
    capability["consultants"].append(email)
    record_audit_event(user["username"], "register", capability_name)
    return {"message": f"Registered {email} for {capability_name}"}


@app.delete("/capabilities/{capability_name}/unregister")
def unregister_from_capability(capability_name: str, email: str,
                               user=Depends(require_practice_lead)):
    """Unregister a consultant from a capability"""
    # Validate capability exists
    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    # Get the specific capability
    capability = capabilities[capability_name]

    # Validate consultant is registered
    if email not in capability["consultants"]:
        raise HTTPException(
            status_code=400,
            detail="Consultant is not registered for this capability"
        )

    # Remove consultant
    capability["consultants"].remove(email)
    record_audit_event(user["username"], "unregister", capability_name)
    return {"message": f"Unregistered {email} from {capability_name}"}
