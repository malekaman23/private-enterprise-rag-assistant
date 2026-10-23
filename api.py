"""
api.py
------
Yeh FastAPI backend hai jo tumhara saara existing logic
(router_agent, document_processor, vector_store, memory, voice_tools,
reminders) ko REST API endpoints ke through expose karta hai - taaki
React frontend inse baat kar sake.

Chalane ke liye:
    uvicorn api:app --reload --port 8000
"""

import os
import shutil
import traceback
import secrets
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import io

import config
import memory
import document_processor
import vector_store
import voice_tools
import reminders as reminders_db
import action_store
import action_executor
import audit_log
import document_submissions
import user_auth
from access_policy import default_required_role, validate_required_role
from connectors import LocalFilesystemConnector
from router_agent import answer_query
from auth import Principal, authenticate
from tenant_utils import DEFAULT_TENANT_ID, DEFAULT_USER_ID, safe_scope
import rate_limit
import data_server_state
from enterprise.connectors import status as connector_status
from enterprise.data_sources import catalog as data_source_catalog

app = FastAPI(title="Personal AI Assistant API")

if config.APP_ENV == "production" and not (
    config.API_AUTH_TOKEN or config.API_TOKENS_JSON or config.OIDC_JWKS_URL
):
    raise RuntimeError(
        "API_AUTH_TOKEN, API_TOKENS_JSON, or OIDC_JWKS_URL must be set when APP_ENV=production"
    )


@app.middleware("http")
async def require_api_auth(request: Request, call_next):
    """Require a bearer token for API routes in production deployments."""
    if config.APP_ENV == "production" and request.url.path.startswith("/api/"):
        if request.method == "OPTIONS" or (
            request.url.path in {"/api/auth/login", "/api/demo/login"}
            or (config.DEMO_MODE and request.url.path == "/api/status")
        ):
            return await call_next(request)
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        principal = authenticate(token) if scheme.lower() == "bearer" else None
        if principal is None:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        request.state.principal = principal
        if not rate_limit.allow(f"{principal.tenant_id}:{principal.user_id}"):
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    else:
        # Development remains convenient, while production always authenticates.
        request.state.principal = Principal(
            tenant_id=request.headers.get("X-Tenant-ID", DEFAULT_TENANT_ID),
            user_id=request.headers.get("X-User-ID", DEFAULT_USER_ID),
        )
    return await call_next(request)


def current_principal(request: Request) -> Principal:
    return request.state.principal


def require_admin(request: Request) -> Principal:
    principal = current_principal(request)
    if "admin" not in principal.roles:
        raise HTTPException(status_code=403, detail="Administrator role required")
    return principal

# CORS - React frontend (alag port pe chalta hai) ko backend se
# baat karne ki permission deta hai
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.API_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory.init_db()
reminders_db.init_reminders_db()


@app.get("/health/live")
def liveness():
    """Process liveness probe; intentionally does not expose configuration."""
    return {"status": "alive"}


@app.get("/health/ready")
def readiness():
    """Readiness probe for a reverse proxy/orchestrator."""
    if config.LLM_PROVIDER in {"local", "ollama"}:
        model_ready = (
            config.is_local_model_ready()
            if config.LLM_PROVIDER == "local"
            else config.is_ollama_running()
        )
    else:
        model_ready = bool(config.get_available_providers())
    if not model_ready:
        raise HTTPException(status_code=503, detail="Configured LLM provider is not ready")
    return {"status": "ready", "provider": config.LLM_PROVIDER}


# ---------------- Request/Response Models ----------------

class ChatRequest(BaseModel):
    question: str
    category: str | None = None
    force_private: bool = False


class ChatResponse(BaseModel):
    answer: str
    source: str
    sources: list[dict] = []


class TTSRequest(BaseModel):
    text: str


class ProviderRequest(BaseModel):
    provider: str


class DemoLoginRequest(BaseModel):
    profile: str


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    display_name: str = ""
    password: str
    roles: list[str] = ["employee"]
    departments: list[str] = []


class UpdateUserRequest(BaseModel):
    username: str
    display_name: str = ""
    password: str | None = None
    roles: list[str] = ["employee"]
    departments: list[str] = []


@app.post("/api/auth/login")
def login(req: LoginRequest):
    token = user_auth.login(req.username, req.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"token": token}


@app.post("/api/demo/login")
def demo_login(req: DemoLoginRequest):
    """Demo-only profile switch; disabled unless DEMO_MODE=true."""
    if not config.DEMO_MODE:
        raise HTTPException(status_code=404, detail="Demo login is disabled")
    identity = config.DEMO_USERS.get(req.profile.strip().lower())
    if not identity:
        raise HTTPException(status_code=400, detail="Unknown demo profile")
    return {
        "token": identity["token"],
        "profile": req.profile.strip().lower(),
        "user_id": identity["user_id"],
        "roles": identity["roles"],
        "departments": identity["departments"],
    }


# ---------------- Chat Endpoints ----------------

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    """Ek sawal bhejo, jawab (source aur konse documents se aaya) wapas milega."""
    try:
        principal = current_principal(request)
        answer, source, sources = answer_query(
            req.question, category=req.category, force_private=req.force_private,
            tenant_id=principal.tenant_id, user_id=principal.user_id,
            departments=principal.departments, roles=principal.roles,
        )
        audit_log.record_event(
            principal.tenant_id, principal.user_id, "chat.completed", "ok",
            {"source": source, "question_length": len(req.question or "")},
        )
        return ChatResponse(answer=answer, source=source, sources=sources)
    except Exception as e:
        principal = current_principal(request)
        audit_log.record_event(
            principal.tenant_id, principal.user_id, "chat.completed", "error",
            {"error_type": type(e).__name__},
        )
        if config.APP_ENV != "production":
            traceback.print_exc()
            detail = str(e)
        else:
            detail = "Internal server error"
        raise HTTPException(status_code=500, detail=detail)


@app.get("/api/history")
def get_history(request: Request, limit: int = 50):
    """Recent conversation history wapas deta hai."""
    principal = current_principal(request)
    rows = memory.get_recent_history(limit=limit, tenant_id=principal.tenant_id, user_id=principal.user_id)
    return [{"role": role, "content": msg} for role, msg in rows]


@app.delete("/api/history")
def clear_history(request: Request):
    """Poori chat history clear kar deta hai."""
    principal = current_principal(request)
    memory.clear_history(tenant_id=principal.tenant_id, user_id=principal.user_id)
    return {"status": "cleared"}


# ---------------- Document Endpoints ----------------

@app.post("/api/documents/upload")
async def upload_documents(
    request: Request,
    files: list[UploadFile] = File(...),
    category: str = Form("General"),
    department: str = Form(""),
    required_role: str = Form(""),
):
    """Documents upload karke process karta hai, ek category ke andar."""
    principal = current_principal(request)
    is_admin_upload = "admin" in principal.roles
    if config.PRODUCT_MODE == "company" and not is_admin_upload:
        # Employees can submit files, but never index or publish them directly.
        department_id = (principal.departments[0] if principal.departments else "").strip().lower()
        role = default_required_role(category, department_id)
    else:
        department_id = department.strip().lower()
        role = validate_required_role(required_role or default_required_role(category, department_id))
    if department_id and not is_admin_upload and principal.departments and department_id not in principal.departments:
        raise HTTPException(status_code=403, detail="Employees can only submit to their own department")
    if department_id and is_admin_upload and "admin" not in principal.roles:
        raise HTTPException(status_code=403, detail="Only administrators can assign department scope")
    tenant_dir = Path(config.DATA_DIR).resolve() / "tenants" / safe_scope(principal.tenant_id, DEFAULT_TENANT_ID)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    new_filenames = []
    if config.PRODUCT_MODE == "company" and not is_admin_upload:
        quarantine_dir = Path(config.DATA_DIR).resolve() / "quarantine" / safe_scope(principal.tenant_id, DEFAULT_TENANT_ID)
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        submissions = []
        for file in files:
            original_name = Path(file.filename or "").name
            suffix = Path(original_name).suffix.lower().lstrip(".")
            if not original_name or suffix not in config.ALLOWED_UPLOAD_EXTENSIONS:
                raise HTTPException(status_code=400, detail="Unsupported or invalid filename")
            target = (quarantine_dir / f"{secrets.token_hex(8)}_{original_name}").resolve()
            size = 0
            with open(target, "wb") as stream:
                while chunk := file.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                        target.unlink(missing_ok=True)
                        raise HTTPException(status_code=413, detail="File is too large")
                    stream.write(chunk)
            submission_id = document_submissions.create(
                principal.tenant_id, principal.user_id, original_name, str(target),
                category.strip() or "General", department_id, role,
            )
            submissions.append(submission_id)
        audit_log.record_event(principal.tenant_id, principal.user_id, "document.submitted", "pending", {"count": len(submissions)})
        return {"status": "pending_approval", "submission_ids": submissions, "files": len(submissions)}

    for file in files:
        original_name = Path(file.filename or "").name
        suffix = Path(original_name).suffix.lower().lstrip(".")
        if not original_name or suffix not in config.ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported or invalid filename")

        filepath = (tenant_dir / original_name).resolve()
        if tenant_dir not in filepath.parents:
            raise HTTPException(status_code=400, detail="Invalid upload path")

        size = 0
        with open(filepath, "wb") as f:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                    filepath.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File is too large")
                f.write(chunk)
        new_filenames.append(original_name)

    chunks = document_processor.process_documents(only_files=new_filenames, data_dir=str(tenant_dir))
    if chunks:
        vector_store.build_vectorstore(
            chunks, category=category, tenant_id=principal.tenant_id,
            owner_user_id=principal.user_id,
            access_scope="tenant" if "admin" in principal.roles else "user",
            department_id=department_id if "admin" in principal.roles else "",
            required_role=role,
        )
        audit_log.record_event(
            principal.tenant_id, principal.user_id, "document.uploaded", "ok",
            {"files": len(new_filenames), "chunks": len(chunks), "category": category},
        )
        return {"status": "success", "chunks_added": len(chunks), "category": category}
    else:
        return {"status": "no_content", "chunks_added": 0}


@app.get("/api/document-submissions")
def list_document_submissions(request: Request, include_completed: bool = False):
    """Employees see their own requests; admins see the tenant queue."""
    p = current_principal(request)
    rows = document_submissions.list_for(
        p.tenant_id,
        user_id=None if "admin" in p.roles else p.user_id,
        include_completed=include_completed if "admin" in p.roles else True,
    )
    for row in rows:
        row.pop("quarantine_path", None)
    return {"submissions": rows}


@app.get("/api/document-submissions/{submission_id}/download")
def download_document_submission(submission_id: int, request: Request):
    """Allow only admins to inspect/download a quarantined employee upload."""
    p = require_admin(request)
    submission = document_submissions.get(submission_id, p.tenant_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    source = Path(submission["quarantine_path"]).resolve()
    if not source.is_file():
        raise HTTPException(status_code=410, detail="Uploaded file is unavailable")
    return FileResponse(str(source), filename=Path(submission["filename"]).name, media_type="application/octet-stream")


class SubmissionReviewRequest(BaseModel):
    note: str = ""


@app.post("/api/document-submissions/{submission_id}/reject")
def reject_document_submission(submission_id: int, req: SubmissionReviewRequest, request: Request):
    p = require_admin(request)
    submission = document_submissions.get(submission_id, p.tenant_id)
    if not submission or submission["status"] != "pending":
        raise HTTPException(status_code=404, detail="Pending submission not found")
    Path(submission["quarantine_path"]).unlink(missing_ok=True)
    if not document_submissions.review(submission_id, p.tenant_id, "rejected", p.user_id, req.note[:1000]):
        raise HTTPException(status_code=409, detail="Submission was already reviewed")
    audit_log.record_event(p.tenant_id, p.user_id, "document.rejected", "ok", {"submission_id": submission_id})
    return {"status": "rejected"}


@app.post("/api/document-submissions/{submission_id}/approve")
def approve_document_submission(submission_id: int, req: SubmissionReviewRequest, request: Request):
    p = require_admin(request)
    submission = document_submissions.get(submission_id, p.tenant_id)
    if not submission or submission["status"] != "pending":
        raise HTTPException(status_code=404, detail="Pending submission not found")
    source = Path(submission["quarantine_path"]).resolve()
    if not source.is_file():
        raise HTTPException(status_code=410, detail="Quarantined file is unavailable")
    approved_dir = Path(config.DATA_DIR).resolve() / "tenants" / safe_scope(p.tenant_id, DEFAULT_TENANT_ID)
    approved_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(submission["filename"]).name
    target = (approved_dir / filename).resolve()
    if target.exists():
        target = (approved_dir / f"{target.stem}-{submission_id}{target.suffix}").resolve()
    if approved_dir not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid approved path")
    try:
        shutil.move(str(source), str(target))
        chunks = document_processor.process_documents(only_files=[target.name], data_dir=str(approved_dir))
        if not chunks:
            raise ValueError("No readable content found")
        vector_store.build_vectorstore(
            chunks, category=submission["category"], tenant_id=p.tenant_id,
            owner_user_id=submission["user_id"], access_scope="tenant",
            department_id=submission["department_id"], required_role=submission["required_role"],
        )
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Document could not be indexed: {exc}")
    if not document_submissions.review(submission_id, p.tenant_id, "approved", p.user_id, req.note[:1000]):
        target.unlink(missing_ok=True)
        vector_store.delete_document(target.name, category=submission["category"], tenant_id=p.tenant_id)
        raise HTTPException(status_code=409, detail="Submission was already reviewed")
    audit_log.record_event(p.tenant_id, p.user_id, "document.approved", "ok", {"submission_id": submission_id})
    return {"status": "approved", "filename": target.name}


@app.get("/api/documents/categories")
def get_categories(request: Request):
    """Ab tak ki saari categories ki list."""
    p = current_principal(request)
    return {"categories": vector_store.get_all_categories(p.tenant_id, p.user_id, p.departments, p.roles)}


@app.get("/api/documents/list")
def get_documents_list(request: Request):
    """Ab tak upload hui saari files ki list (filename, category, chunk count)."""
    p = current_principal(request)
    return {"documents": vector_store.list_documents(p.tenant_id, p.user_id, p.departments, p.roles)}


@app.delete("/api/documents/{filename:path}")
def delete_document(filename: str, request: Request, category: str | None = None):
    """Ek document ko vectorstore se aur disk se delete karta hai."""
    principal = require_admin(request)
    safe_name = Path(filename or "").name
    if not safe_name or safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    deleted_count = vector_store.delete_document(
        safe_name, category=category, tenant_id=principal.tenant_id
    )

    tenant_dir = Path(config.DATA_DIR).resolve() / "tenants" / safe_scope(principal.tenant_id, DEFAULT_TENANT_ID)
    filepath = (tenant_dir / safe_name).resolve()
    if tenant_dir not in filepath.parents:
        raise HTTPException(status_code=400, detail="Invalid file path")
    if os.path.exists(filepath):
        os.remove(filepath)

    audit_log.record_event(
        principal.tenant_id, principal.user_id, "document.deleted", "ok",
        {"filename_hash": audit_log.digest(safe_name), "chunks_removed": deleted_count},
    )

    return {"status": "deleted", "chunks_removed": deleted_count}


@app.get("/api/documents/download")
def download_document(request: Request, filename: str):
    """Download only a document visible to the authenticated principal."""
    p = current_principal(request)
    safe_name = Path(filename or "").as_posix()
    if not safe_name or safe_name.startswith("/") or ".." in Path(safe_name).parts:
        raise HTTPException(status_code=400, detail="Invalid filename")

    visible_names = {item["filename"] for item in vector_store.list_documents(p.tenant_id, p.user_id, p.departments, p.roles)}
    if safe_name not in visible_names:
        raise HTTPException(status_code=404, detail="Document not found")

    candidates = [
        Path(config.DATA_DIR).resolve() / "tenants" / safe_scope(p.tenant_id, DEFAULT_TENANT_ID) / safe_name,
    ]
    if p.tenant_id == DEFAULT_TENANT_ID:
        candidates.append(Path(config.DATA_DIR).resolve() / safe_name)
    if config.COMPANY_DATA_ROOT:
        candidates.append(Path(config.COMPANY_DATA_ROOT).expanduser().resolve() / safe_name)

    for candidate in candidates:
        resolved = candidate.resolve()
        allowed_roots = [root.resolve() for root in [
            Path(config.DATA_DIR).resolve() / "tenants" / safe_scope(p.tenant_id, DEFAULT_TENANT_ID),
            Path(config.DATA_DIR).resolve(),
            Path(config.COMPANY_DATA_ROOT).expanduser().resolve() if config.COMPANY_DATA_ROOT else None,
        ] if root is not None]
        if any(root == resolved or root in resolved.parents for root in allowed_roots) and resolved.is_file():
            audit_log.record_event(p.tenant_id, p.user_id, "document.downloaded", "ok", {"filename_hash": audit_log.digest(safe_name)})
            return FileResponse(str(resolved), filename=Path(safe_name).name)
    raise HTTPException(status_code=404, detail="Document file is unavailable")


# ---------------- Reminders Endpoints ----------------

@app.get("/api/reminders")
def list_reminders(request: Request, include_done: bool = False):
    p = current_principal(request)
    text = reminders_db.list_reminders(include_done=include_done, tenant_id=p.tenant_id, user_id=p.user_id)
    return {"reminders": text}


@app.get("/api/reminders/list")
def list_reminders_structured(request: Request, include_done: bool = True):
    """UI ke liye structured format - har reminder alag object mein."""
    p = current_principal(request)
    return {"reminders": reminders_db.list_reminders_structured(include_done=include_done, tenant_id=p.tenant_id, user_id=p.user_id)}


@app.patch("/api/reminders/{reminder_id}/done")
def mark_reminder_done(reminder_id: int, request: Request):
    p = current_principal(request)
    result = reminders_db.mark_done(reminder_id, tenant_id=p.tenant_id, user_id=p.user_id)
    return {"status": "done", "message": result}


@app.delete("/api/reminders/{reminder_id}")
def delete_reminder(reminder_id: int, request: Request):
    p = current_principal(request)
    result = reminders_db.delete_reminder(reminder_id, tenant_id=p.tenant_id, user_id=p.user_id)
    return {"status": "deleted", "message": result}


# ---------------- Approval queue / audit ----------------

@app.get("/api/actions/pending")
def pending_actions(request: Request):
    p = current_principal(request)
    return {"actions": action_store.list_actions(p.tenant_id)} if "admin" in p.roles else {
        "actions": action_store.list_actions(p.tenant_id, user_id=p.user_id)
    }


@app.post("/api/actions/{action_id}/approve")
def approve_action(action_id: int, request: Request):
    p = require_admin(request)
    action = action_store.get_action(action_id, p.tenant_id)
    if not action or action["status"] != "pending":
        raise HTTPException(status_code=404, detail="Pending action not found")
    if not action_store.review_action(action_id, p.tenant_id, "approved", p.user_id):
        raise HTTPException(status_code=409, detail="Action was already reviewed")
    try:
        result = action_executor.execute(action["action_type"], action["payload"])
        action_store.set_status(action_id, p.tenant_id, "completed")
        audit_log.record_event(p.tenant_id, p.user_id, "action.completed", "ok", {"action_id": action_id})
        return {"status": "completed", "message": result}
    except Exception as exc:
        action_store.set_status(action_id, p.tenant_id, "failed")
        audit_log.record_event(p.tenant_id, p.user_id, "action.completed", "error", {"action_id": action_id, "error_type": type(exc).__name__})
        raise HTTPException(status_code=502, detail="Approved action execution failed")


@app.post("/api/actions/{action_id}/reject")
def reject_action(action_id: int, request: Request):
    p = require_admin(request)
    if not action_store.review_action(action_id, p.tenant_id, "rejected", p.user_id):
        raise HTTPException(status_code=404, detail="Pending action not found")
    audit_log.record_event(p.tenant_id, p.user_id, "action.rejected", "ok", {"action_id": action_id})
    return {"status": "rejected"}


@app.get("/api/audit")
def get_audit(request: Request, limit: int = 100):
    p = require_admin(request)
    return {"events": audit_log.list_events(p.tenant_id, limit=limit)}


@app.post("/api/connectors/filesystem/sync")
def sync_filesystem_connector(request: Request):
    """Index a configured read-only company/NAS folder into the tenant RAG store."""
    p = require_admin(request)
    if not config.COMPANY_DATA_ROOT:
        raise HTTPException(status_code=400, detail="COMPANY_DATA_ROOT is not configured")
    if not data_server_state.is_enabled():
        raise HTTPException(status_code=409, detail="Company data server is disconnected")
    try:
        connector = LocalFilesystemConnector(config.COMPANY_DATA_ROOT)
        relative_files = list(connector.files())
        # Company Server is a dedicated source category. Replacing that
        # category on every sync keeps deletions and renames from leaving
        # stale chunks searchable after the source file is gone.
        try:
            vector_store.delete_category("Company Server", tenant_id=p.tenant_id)
        except Exception:
            # First syncs may not have a vector store yet.
            pass
        if not relative_files:
            return {"status": "no_content", "files_seen": 0, "chunks_added": 0}

        chunks = document_processor.process_documents(
            only_files=relative_files, data_dir=str(connector.root)
        )
        if chunks:
            grouped = {}
            for chunk in chunks:
                source_name = str(chunk.metadata.get("source_file", ""))
                top_level = source_name.split("/", 1)[0] if source_name else ""
                role = default_required_role(top_level, top_level)
                department_id = top_level.lower() if role in {"hr", "finance", "sales"} else ""
                grouped.setdefault((role, department_id), []).append(chunk)
            for (role, department_id), role_chunks in grouped.items():
                vector_store.build_vectorstore(
                    role_chunks, category="Company Server", tenant_id=p.tenant_id,
                    owner_user_id=p.user_id, access_scope="tenant",
                    required_role=role,
                    department_id=department_id,
                )
        audit_log.record_event(
            p.tenant_id, p.user_id, "connector.filesystem_sync", "ok",
            {"files_seen": len(relative_files), "chunks": len(chunks)},
        )
        return {"status": "success", "files_seen": len(relative_files), "chunks_added": len(chunks)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        audit_log.record_event(
            p.tenant_id, p.user_id, "connector.filesystem_sync", "error",
            {"error_type": type(exc).__name__},
        )
        raise HTTPException(status_code=500, detail="Filesystem sync failed")


@app.get("/api/admin/diagnostics")
def admin_diagnostics(request: Request):
    """Return a redacted deployment readiness snapshot for administrators."""
    p = require_admin(request)
    try:
        indexed = vector_store.list_documents(p.tenant_id, p.user_id, p.departments, p.roles)
    except Exception:
        indexed = []
    return {
        "mode": config.PRODUCT_MODE,
        "demo_mode": config.DEMO_MODE,
        "environment": config.APP_ENV,
        "company_data_server": {
            "configured": bool(config.COMPANY_DATA_ROOT),
            "enabled": data_server_state.is_enabled(),
            "read_only": True,
        },
        "security": {
            "api_authentication": bool(config.API_AUTH_TOKEN or config.API_TOKENS_JSON or config.OIDC_JWKS_URL),
            "oidc_configured": bool(config.OIDC_JWKS_URL),
            "cloud_document_context": config.ALLOW_CLOUD_DOCUMENT_CONTEXT,
            "rate_limit_enabled": bool(config.REDIS_URL),
        },
        "storage": {
            "indexed_documents": len(indexed),
            "postgres_configured": bool(config.DATABASE_URL),
        },
        "connectors": connector_status(),
    }


# ---------------- Voice Endpoints ----------------

@app.post("/api/voice/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Audio file upload karo, text wapas milega."""
    audio_bytes = await audio.read()
    filename = audio.filename or "audio.wav"
    text = voice_tools.transcribe_audio(audio_bytes)
    return {"text": text}


@app.post("/api/voice/speak")
def speak(req: TTSRequest):
    """Text bhejo, mp3 audio stream wapas milega."""
    audio_bytes = voice_tools.text_to_speech(req.text)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="TTS generation failed")
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")


# ---------------- Config/Status Endpoint ----------------

@app.get("/api/status")
def status():
    """Frontend ko batata hai konsa LLM provider active hai, etc."""
    return {
        "mode": config.PRODUCT_MODE,
        "demo_mode": config.DEMO_MODE,
        "provider": config.LLM_PROVIDER,
        "model": config.MODEL_NAMES.get(config.LLM_PROVIDER, "unknown"),
        "available_providers": config.get_available_providers(),
    }


@app.get("/api/admin/integrations")
def integration_status(request: Request):
    """Safe connector status; never returns endpoints, tokens, or payloads."""
    require_admin(request)
    return {"connectors": connector_status()}


@app.get("/api/admin/users")
def admin_users(request: Request):
    p = require_admin(request)
    return {"users": user_auth.list_users(p.tenant_id)}


@app.post("/api/admin/users")
def admin_create_user(req: CreateUserRequest, request: Request):
    p = require_admin(request)
    allowed_roles = {"employee", "sales", "hr", "finance", "manager", "executive", "admin"}
    roles = [str(role).strip().lower() for role in req.roles if str(role).strip().lower() in allowed_roles]
    if not roles:
        raise HTTPException(status_code=400, detail="At least one valid role is required")
    if "admin" in roles and "admin" not in p.roles:
        raise HTTPException(status_code=403, detail="Only administrators can create administrators")
    try:
        user_id = user_auth.create_user(req.username, req.display_name, req.password, roles, req.departments, p.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    audit_log.record_event(p.tenant_id, p.user_id, "user.created", "ok", {"username_hash": audit_log.digest(req.username), "roles": roles})
    return {"status": "created", "id": user_id, "username": req.username.strip().lower()}


@app.patch("/api/admin/users/{user_id}")
def admin_set_user(user_id: int, req: UpdateUserRequest, request: Request):
    p = require_admin(request)
    allowed_roles = {"employee", "sales", "hr", "finance", "manager", "executive", "admin"}
    roles = [str(role).strip().lower() for role in req.roles if str(role).strip().lower() in allowed_roles]
    if not roles:
        raise HTTPException(status_code=400, detail="At least one valid role is required")
    if "admin" in roles and "admin" not in p.roles:
        raise HTTPException(status_code=403, detail="Only administrators can assign administrator role")
    if user_id == p.user_id and "admin" not in roles:
        raise HTTPException(status_code=400, detail="You cannot remove administrator access from your own account")
    try:
        updated = user_auth.update_user(user_id, p.tenant_id, req.username, req.display_name, req.password, roles, req.departments)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    audit_log.record_event(p.tenant_id, p.user_id, "user.updated", "ok", {"user_id": user_id, "roles": roles, "password_changed": bool(req.password)})
    return {"status": "updated", "id": user_id}


@app.post("/api/admin/users/{user_id}/enabled")
def admin_toggle_user(user_id: int, enabled: bool, request: Request):
    p = require_admin(request)
    if user_id == p.user_id and not enabled:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    if not user_auth.set_enabled(user_id, p.tenant_id, enabled):
        raise HTTPException(status_code=404, detail="User not found")
    audit_log.record_event(p.tenant_id, p.user_id, "user.enabled_changed", "ok", {"user_id": user_id, "enabled": enabled})
    return {"status": "updated", "enabled": enabled}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, request: Request):
    p = require_admin(request)
    if user_id == p.user_id:
        raise HTTPException(status_code=400, detail="You cannot remove your own account")
    if not user_auth.delete_user(user_id, p.tenant_id):
        raise HTTPException(status_code=404, detail="User not found")
    audit_log.record_event(p.tenant_id, p.user_id, "user.deleted", "ok", {"user_id": user_id})
    return {"status": "deleted", "id": user_id}


@app.get("/api/admin/connections")
def connection_status(request: Request):
    """UI-safe connection overview; never exposes paths, URLs, or secrets."""
    require_admin(request)
    mounted = bool(config.COMPANY_DATA_ROOT)
    enabled = data_server_state.is_enabled()
    return {
        "data_server": {
            "configured": mounted and enabled,
            "mounted": mounted,
            "enabled": enabled,
            "mode": "read_only_filesystem" if mounted and enabled else ("disconnected" if mounted else "not_configured"),
        },
        "phone": {
            "configured": False,
            "mode": "companion_app_required",
        },
        "connectors": connector_status(),
    }


@app.get("/api/admin/data-sources")
def data_sources(request: Request):
    """Return every supported source type without exposing credentials."""
    require_admin(request)
    return {"sources": data_source_catalog()}


class DataServerStateRequest(BaseModel):
    enabled: bool


@app.post("/api/admin/data-server")
def set_data_server_state(req: DataServerStateRequest, request: Request):
    """Enable/disable indexing of the mounted company share at runtime."""
    p = require_admin(request)
    if not config.COMPANY_DATA_ROOT:
        raise HTTPException(status_code=400, detail="COMPANY_DATA_ROOT is not configured")
    data_server_state.set_enabled(req.enabled)
    removed = 0
    if not req.enabled:
        try:
            removed = vector_store.delete_category("Company Server", tenant_id=p.tenant_id)
        except Exception:
            removed = 0
    audit_log.record_event(
        p.tenant_id, p.user_id, "connector.filesystem_state",
        "disabled" if not req.enabled else "enabled", {"indexed_chunks_removed": removed},
    )
    return {"enabled": req.enabled, "indexed_chunks_removed": removed}


@app.post("/api/settings/provider")
def switch_provider(req: ProviderRequest, request: Request):
    """LLM provider ko runtime mein badalta hai (bina restart ke)."""
    require_admin(request)
    try:
        new_provider = config.set_provider(req.provider)
        return {
            "status": "switched",
            "provider": new_provider,
            "model": config.MODEL_NAMES.get(new_provider, "unknown"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
