# SPDX-FileCopyrightText: 2026 Siddhant Tiwari
# SPDX-License-Identifier: AGPL-3.0-only
"""API smoke tests mock inference and isolate all database/upload writes."""

import io
import runpy
from unittest.mock import Mock
from pathlib import Path
from types import SimpleNamespace
import zipfile

from fastapi.testclient import TestClient
import pytest

import database
import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "synthetic.db"))
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(main, "UPLOAD_DIR", str(uploads))
    processor = SimpleNamespace(
        pipe=object(),
        transcribe=lambda path: ("Synthetic lecture transcript.", []),
    )
    engine = SimpleNamespace(extract_topics=lambda transcript, course_name=None: [
        "Synthetic Topic A", "Synthetic Topic B", "Synthetic Topic C",
        "Synthetic Topic D", "Synthetic Topic E",
    ])
    monkeypatch.setattr(main, "audio_processor", None)
    monkeypatch.setattr(main, "nlp_engine", None)
    monkeypatch.setattr(main, "get_processor", lambda: processor)
    monkeypatch.setattr(main, "get_engine", lambda: engine)
    monkeypatch.setattr(main, "check_ollama_status", lambda: {"status": "healthy"})
    with TestClient(main.app) as test_client:
        yield test_client
    assert list(uploads.iterdir()) == []


@pytest.mark.parametrize("path", [
    "/", "/record", "/student", "/dashboard", "/docs", "/openapi.json",
    "/static/app.js", "/static/topic-details.html", "/license",
])
def test_public_routes(client, path):
    assert client.get(path).status_code == 200


def test_health_uses_pipeline_attribute(client):
    body = client.get("/health").json()
    assert body["database"] == "healthy"
    assert body["audio_processor"] == "ready"


def test_empty_state(client):
    assert client.get("/topics/latest").status_code == 404
    assert client.get("/dashboard-stats").status_code == 404
    assert client.get("/session/999").status_code == 404


def test_mocked_upload_feedback_and_statistics(client):
    uploaded = client.post(
        "/upload-audio",
        files={"file": ("synthetic.wav", b"synthetic mocked audio", "audio/wav")},
        data={"course_name": "Synthetic Course"},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["session_id"] == 1
    topics = client.get("/topics/latest").json()
    assert len(topics) == 5
    response = client.post("/submit-feedback", json={"feedback": [
        {"topic_id": t["topic_id"], "rating": 8} for t in topics
    ]})
    assert response.status_code == 200
    assert response.json()["feedback_count"] == 5
    assert client.get("/dashboard-stats").json()[0]["avg_rating"] == 8
    assert client.get("/session/1").json()["transcript_text"] == "Synthetic lecture transcript."


@pytest.mark.parametrize("payload", [
    {"feedback": []},
    {"feedback": [{"topic_id": 1, "rating": 11}]},
    {"feedback": [{"topic_id": 1, "rating": 0}]},
    {"feedback": [{"topic_id": 1, "rating": 5}] * 11},
])
def test_feedback_validation(client, payload):
    assert client.post("/submit-feedback", json=payload).status_code == 422


def test_unsupported_upload(client):
    assert client.post(
        "/upload-audio", files={"file": ("synthetic.txt", b"synthetic", "text/plain")}
    ).status_code == 400


def test_source_offer_contains_only_explicit_public_files(client):
    response = client.get("/source")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {f"rift/{name}" for name in main.SOURCE_FILES}
        assert all(not n.endswith((".pem", ".db", ".pyc", ".pdf")) for n in archive.namelist())
        assert archive.read("rift/LICENSE") == Path("LICENSE").read_bytes()
        assert archive.read("rift/main.py") == Path("main.py").read_bytes()


def test_source_offer_rejects_missing_file(client, monkeypatch):
    monkeypatch.setattr(main, "SOURCE_FILES", ("nonexistent-source.py",))
    assert client.get("/source").status_code == 503


def test_source_offer_rejects_parent_traversal(client, monkeypatch):
    monkeypatch.setattr(main, "SOURCE_FILES", ("../private.txt",))
    assert client.get("/source").status_code == 503


def test_same_origin_default_does_not_allow_cross_origin_access(client):
    response = client.options("/submit-feedback", headers={
        "Origin": "https://example.invalid", "Access-Control-Request-Method": "POST",
    })
    assert "access-control-allow-origin" not in response.headers


def test_launcher_defaults_to_loopback_without_legacy_tls(monkeypatch):
    for name in ["RIFT_HOST", "RIFT_PORT", "RIFT_SSL_KEYFILE", "RIFT_SSL_CERTFILE"]:
        monkeypatch.delenv(name, raising=False)
    run = Mock()
    monkeypatch.setattr("uvicorn.run", run)
    runpy.run_path(str(Path(main.__file__)), run_name="__main__")
    assert run.call_args.kwargs["host"] == "127.0.0.1"
    assert run.call_args.kwargs["port"] == 8000
    assert "ssl_keyfile" not in run.call_args.kwargs
    assert "ssl_certfile" not in run.call_args.kwargs


def test_launcher_refuses_incomplete_tls_configuration(monkeypatch):
    monkeypatch.setenv("RIFT_SSL_KEYFILE", "synthetic-missing-key.pem")
    monkeypatch.delenv("RIFT_SSL_CERTFILE", raising=False)
    run = Mock()
    monkeypatch.setattr("uvicorn.run", run)
    with pytest.raises(SystemExit, match="Set both"):
        runpy.run_path(str(Path(main.__file__)), run_name="__main__")
    run.assert_not_called()
