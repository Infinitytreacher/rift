# SPDX-FileCopyrightText: 2026 Siddhant Tiwari
# SPDX-License-Identifier: AGPL-3.0-only
# RIFT is distributed without warranty. See LICENSE and COPYRIGHT.md.



"""
Main FastAPI Application for IoT Anonymous Feedback System
Provides REST API endpoints for audio upload, topic retrieval, feedback submission,
and dashboard statistics.
"""

import io
import os
from pathlib import Path
import zipfile
import tempfile
import logging
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Local imports
from database import (
    init_database,
    create_session,
    get_latest_session,
    get_session_by_id,
    create_topics,
    get_latest_topics,
    submit_bulk_feedback,
    get_dashboard_stats
)
from audio_processor import (
    AudioProcessor,
    validate_audio_file,
    get_processor
)
from nlp_engine import (
    NLPEngine,
    get_engine,
    check_ollama_status
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_DIR = os.environ.get(
    "RIFT_UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads")
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Global processor instances
audio_processor: Optional[AudioProcessor] = None
nlp_engine: Optional[NLPEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global audio_processor, nlp_engine
    
    logger.info("Starting up IoT Feedback System...")
    
    init_database()
    logger.info("Database initialized")
    
    try:
        audio_processor = get_processor()
        logger.info("Audio processor initialized")
    except Exception as e:
        logger.warning(f"Audio processor initialization deferred: {e}")
    
    try:
        status = check_ollama_status()
        if status.get('status') == 'healthy':
            nlp_engine = get_engine()
            logger.info(f"NLP engine connected: {status.get('configured_model')}")
        else:
            logger.warning(f"NLP engine unavailable: {status}")
    except Exception as e:
        logger.warning(f"NLP engine initialization deferred: {e}")
    
    yield
    
    logger.info("Shutting down IoT Feedback System...")

app = FastAPI(
    title="IoT Anonymous Feedback System",
    description="A system for capturing lecture audio, extracting topics, and collecting anonymous student feedback",
    version="1.0.0",
    lifespan=lifespan
)

# Same-origin browser access needs no CORS permission. Cross-origin access is opt-in.
allowed_origins = [
    origin.strip() for origin in os.environ.get("RIFT_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Explicit source offer: never archive the working tree or Git history.
# Keep this list current when adding first-party source or build instructions.
SOURCE_FILES = (
    ".gitignore", "LICENSE", "COPYRIGHT.md", "THIRD_PARTY_NOTICES.md",
    "README.md", "SECURITY.md", "PUBLICATION_REVIEW.md",
    "requirements.txt", "requirements-dev.txt",
    "main.py", "database.py", "audio_processor.py", "nlp_engine.py",
    "static/app.js", "static/student.html", "static/dashboard.html",
    "static/record.html", "static/topic-details.html",
    "tests/test_database.py", "tests/test_nlp_engine.py", "tests/test_api.py",
    "tests/test_audio_processor.py",
    "tests/test_frontend.js",
)


@app.get("/license", include_in_schema=False)
async def license_document():
    return FileResponse(Path(__file__).parent / "LICENSE", media_type="text/plain")


@app.get("/source", include_in_schema=False)
async def source_archive():
    root = Path(__file__).resolve().parent
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in SOURCE_FILES:
            path = root / name
            # Reject links, including linked parent directories, to avoid local data leaks.
            if path.resolve() != path.absolute() or not path.is_file():
                raise HTTPException(status_code=503, detail="Source archive unavailable")
            archive.writestr(f"rift/{name}", path.read_bytes())
    return Response(
        output.getvalue(), media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="rift-source.zip"'}
    )


# ==================== Pydantic Models ====================

class FeedbackItem(BaseModel):
    topic_id: int = Field(..., description="Topic identifier")
    rating: int = Field(..., ge=1, le=10, description="Rating from 1-10")
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('Rating must be between 1 and 10')
        return v

class FeedbackSubmission(BaseModel):
    feedback: List[FeedbackItem] = Field(..., min_length=1, max_length=10)

class TopicResponse(BaseModel):
    topic_id: int
    topic_name: str
    session_id: int

class DashboardStats(BaseModel):
    topic_id: int
    topic_name: str
    response_count: int
    avg_rating: Optional[float]
    variance: float

class AudioUploadResponse(BaseModel):
    session_id: int
    transcript_length: int
    topics: List[str]
    message: str

class HealthResponse(BaseModel):
    status: str
    database: str
    audio_processor: str
    nlp_engine: dict

# ==================== HTML Routes ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>IoT Feedback System</title>
        <meta http-equiv="refresh" content="0; url=/student">
    </head>
    <body>
        <p>Redirecting to <a href="/student">Student Survey</a>...</p>
    </body>
    </html>
    """

@app.get("/student", response_class=HTMLResponse)
async def student_page():
    student_html = os.path.join(static_dir, "student.html")
    if os.path.exists(student_html):
        return FileResponse(student_html)
    raise HTTPException(status_code=404, detail="Student page not found")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    dashboard_html = os.path.join(static_dir, "dashboard.html")
    if os.path.exists(dashboard_html):
        return FileResponse(dashboard_html)
    raise HTTPException(status_code=404, detail="Dashboard page not found")

@app.get("/record", response_class=HTMLResponse)
async def record_page():
    record_html = os.path.join(static_dir, "record.html")
    if os.path.exists(record_html):
        return FileResponse(record_html)
    raise HTTPException(status_code=404, detail="Record page not found")

# ==================== API Endpoints ====================

@app.post("/upload-audio", response_model=AudioUploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    course_name: Optional[str] = Form(None)
):
    global audio_processor, nlp_engine
    
    allowed_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {allowed_extensions}"
        )
    
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=file_ext,
        dir=UPLOAD_DIR
    )
    
    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        logger.info(f"Processing uploaded audio ({len(content)} bytes)")
        
        is_valid, message = validate_audio_file(temp_file.name)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid audio file: {message}")
        
        if audio_processor is None:
            audio_processor = get_processor()
        
        logger.info("Starting transcription...")
        transcript_text, segments = audio_processor.transcribe(temp_file.name)
        
        if not transcript_text.strip():
            raise HTTPException(
                status_code=422,
                detail="Transcription produced empty result. Audio may be silent or corrupted."
            )
        
        logger.info(f"Transcription complete: {len(transcript_text)} characters")
        
        logger.info("Extracting topics...")
        if nlp_engine is None:
            nlp_engine = get_engine()
        
        try:
            # Explicitly calling extract_topics to get a List, passing the course context
            topics = nlp_engine.extract_topics(transcript_text, course_name=course_name)
        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            raise HTTPException(
                status_code=500,
                detail="Topic extraction failed. Check the local server logs."
            )
        
        if not topics:
            raise HTTPException(
                status_code=422,
                detail="No topics could be extracted from the transcript."
            )
        
        session_id = create_session(transcript_text)
        create_topics(session_id, topics)
        
        logger.info(f"Created session {session_id} with {len(topics)} topics")
        
        return AudioUploadResponse(
            session_id=session_id,
            transcript_length=len(transcript_text),
            topics=topics,
            message="Audio processed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio processing failed: {e}")
        raise HTTPException(status_code=500, detail="Audio processing failed")
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@app.get("/topics/latest", response_model=List[TopicResponse])
async def get_latest_topics_endpoint():
    topics = get_latest_topics()
    
    if not topics:
        raise HTTPException(
            status_code=404,
            detail="No topics available. Upload a lecture audio first."
        )
    
    return [
        TopicResponse(
            topic_id=t['topic_id'],
            topic_name=t['topic_name'],
            session_id=t['session_id']
        )
        for t in topics
    ]

@app.post("/submit-feedback")
async def submit_feedback(feedback: FeedbackSubmission):
    if not feedback.feedback:
        raise HTTPException(status_code=400, detail="No feedback provided")
    
    feedback_data = [
        {'topic_id': item.topic_id, 'rating': item.rating}
        for item in feedback.feedback
    ]
    
    try:
        feedback_ids = submit_bulk_feedback(feedback_data)
        logger.info(f"Submitted {len(feedback_ids)} feedback entries")
        
        return {
            "success": True,
            "message": f"Thank you! {len(feedback_ids)} ratings submitted.",
            "feedback_count": len(feedback_ids)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@app.get("/dashboard-stats", response_model=List[DashboardStats])
async def get_dashboard_stats_endpoint():
    stats = get_dashboard_stats()
    
    if not stats:
        raise HTTPException(
            status_code=404,
            detail="No data available. Upload audio and collect feedback first."
        )
    
    return [
        DashboardStats(
            topic_id=s['topic_id'],
            topic_name=s['topic_name'],
            response_count=s['response_count'],
            avg_rating=s['avg_rating'],
            variance=s['variance']
        )
        for s in stats
    ]

@app.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        get_latest_session()
        db_status = "healthy"
    except Exception as e:
        db_status = "error"
    
    try:
        if audio_processor and audio_processor.pipe is not None:
            ap_status = "ready"
        else:
            ap_status = "not initialized"
    except Exception as e:
        ap_status = "error"
    
    try:
        nlp_status = check_ollama_status()
    except Exception as e:
        nlp_status = {"status": "error", "error": str(e)}
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        audio_processor=ap_status,
        nlp_engine=nlp_status
    )

@app.get("/session/{session_id}")
async def get_session(session_id: int):
    session = get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn

    # Never silently reuse the private key from the original course submission.
    ssl_keyfile = os.environ.get("RIFT_SSL_KEYFILE")
    ssl_certfile = os.environ.get("RIFT_SSL_CERTFILE")
    host = os.environ.get("RIFT_HOST", "127.0.0.1")
    port = int(os.environ.get("RIFT_PORT", "8000"))

    ssl_config = {}
    if ssl_keyfile or ssl_certfile:
        if not (ssl_keyfile and ssl_certfile):
            raise SystemExit("Set both RIFT_SSL_KEYFILE and RIFT_SSL_CERTFILE for HTTPS.")
        if not (os.path.isfile(ssl_keyfile) and os.path.isfile(ssl_certfile)):
            raise SystemExit("Configured TLS key or certificate does not exist.")
        ssl_config = {"ssl_keyfile": ssl_keyfile, "ssl_certfile": ssl_certfile}

    scheme = "https" if ssl_config else "http"
    print("IoT Anonymous Feedback System")
    print(f"Listening on {scheme}://{host}:{port}")
    print("Interfaces: /record, /student, /dashboard, /docs")
    print("Use only on a trusted local network. No authentication is implemented.")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
        **ssl_config
    )

