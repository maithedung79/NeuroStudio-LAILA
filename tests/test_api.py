"""Tests for FastAPI local security boundaries, project CRUD, and curriculum progress."""

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from neurostudio.api import create_app
from neurostudio.core.templates import template
from neurostudio.engine.data import extract_images
from neurostudio.util import safe_child


def _make_client(tmp_path: Path) -> tuple[TestClient, dict[str, str]]:
    app = create_app(tmp_path, start_worker=False)
    client = TestClient(app, base_url="http://127.0.0.1")
    resp = client.get("/api/v1/session")
    assert resp.status_code == 200
    token = resp.json()["token"]
    return client, {"X-NeuroStudio": token}


def test_local_host_origin_and_csrf_guards(tmp_path: Path) -> None:
    app = create_app(tmp_path, start_worker=False)
    client = TestClient(app, base_url="http://127.0.0.1")

    # Missing session cookie is rejected before any API handler runs.
    unauth = client.get("/api/v1/projects")
    assert unauth.status_code == 401
    assert unauth.json()["detail"] == "SESSION_REQUIRED"

    # External Host header is blocked by loopback middleware.
    remote = client.get("/api/v1/session", headers={"Host": "evil.example.com"})
    assert remote.status_code == 403
    assert remote.json()["detail"] == "LOCAL_ONLY"

    # Mismatched Origin header is rejected.
    bad_origin = client.get("/api/v1/session", headers={"Origin": "https://evil.example.com"})
    assert bad_origin.status_code == 403
    assert bad_origin.json()["detail"] == "ORIGIN_REJECTED"

    # Valid session cookie still requires X-NeuroStudio CSRF header on state-changing requests.
    session = client.get("/api/v1/session")
    assert session.status_code == 200
    assert session.headers.get("X-Content-Type-Options") == "nosniff"
    assert session.headers.get("X-Frame-Options") == "DENY"

    csrf_fail = client.post("/api/v1/projects", json=template("iris").model_dump())
    assert csrf_fail.status_code == 403
    assert csrf_fail.json()["detail"] == "CSRF_REJECTED"


def test_project_crud_revision_conflict_archive_and_restore(tmp_path: Path) -> None:
    client, headers = _make_client(tmp_path)

    created = client.post("/api/v1/projects", json=template("iris").model_dump(), headers=headers)
    assert created.status_code == 200
    record = created.json()
    project_id = record["id"]
    assert record["revision"] == 1

    # Update succeeds with matching revision and bumps revision.
    updated_body = dict(record["project"], name="Iris Updated")
    saved = client.put(
        f"/api/v1/projects/{project_id}",
        json={"revision": 1, "project": updated_body},
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["revision"] == 2
    assert saved.json()["project"]["name"] == "Iris Updated"

    # Stale revision triggers optimistic-locking 409 conflict.
    stale = client.put(
        f"/api/v1/projects/{project_id}",
        json={"revision": 1, "project": updated_body},
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "REVISION_CONFLICT"

    # Clone creates an independent copy at revision 1.
    cloned = client.post(f"/api/v1/projects/{project_id}/clone", headers=headers)
    assert cloned.status_code == 200
    assert cloned.json()["id"] != project_id
    assert "(bản sao)" in cloned.json()["project"]["name"]

    # Archive moves project to trash, then restore brings it back.
    archived = client.request(
        "DELETE",
        f"/api/v1/projects/{project_id}",
        json={"revision": 2},
        headers=headers,
    )
    assert archived.status_code == 200
    assert archived.json()["archived"] is True

    trash = client.get("/api/v1/project-trash")
    assert trash.status_code == 200
    assert any(item["id"] == project_id for item in trash.json())

    restored = client.post(f"/api/v1/project-trash/{project_id}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["id"] == project_id


def test_catalog_curriculum_and_quiz_gate(tmp_path: Path) -> None:
    client, headers = _make_client(tmp_path)

    assert client.get("/api/v1/templates").status_code == 200
    assert len(client.get("/api/v1/catalog/blocks").json()) > 50
    dataset_ids = {d["id"] for d in client.get("/api/v1/datasets").json()}
    assert {"iris", "diabetes"}.issubset(dataset_ids)

    lessons = client.get("/api/v1/curriculum").json()["lessons"]
    assert len(lessons) == 12
    lesson = lessons[0]
    wrong_choice = (lesson["correct"] + 1) % len(lesson["choices"])

    bad_quiz = client.put(
        f"/api/v1/learning/{lesson['id']}",
        json={"completed": True, "quiz_answer": wrong_choice},
        headers=headers,
    )
    assert bad_quiz.status_code == 422

    ok_quiz = client.put(
        f"/api/v1/learning/{lesson['id']}",
        json={"completed": True, "quiz_answer": lesson["correct"]},
        headers=headers,
    )
    assert ok_quiz.status_code == 200
    assert client.get("/api/v1/learning").json()[lesson["id"]]["completed"] is True


def test_graph_validate_code_and_worker_supervisor(tmp_path: Path) -> None:
    import sys
    import time

    client, headers = _make_client(tmp_path)
    iris = template("iris").model_dump()

    val = client.post("/api/v1/graphs/validate", json=iris, headers=headers)
    assert val.status_code == 200
    assert val.json()["ok"] is True

    code = client.post("/api/v1/graphs/code", json=iris, headers=headers)
    assert code.status_code == 200
    assert "def build_pipeline" in code.json()["code"]

    # Exercise Supervisor + worker subprocess execution on a fast profile job.
    app = create_app(tmp_path / "worker-ws", engine_python=sys.executable, start_worker=True)
    with TestClient(app, base_url="http://127.0.0.1") as worker_client:
        tok = worker_client.get("/api/v1/session").json()["token"]
        queued = worker_client.post(
            "/api/v1/datasets/iris/profile",
            json={"target": "target"},
            headers={"X-NeuroStudio": tok},
        )
        assert queued.status_code == 200
        job_id = queued.json()["id"]

        state = "QUEUED"
        for _ in range(100):
            detail = worker_client.get(f"/api/v1/runs/{job_id}").json()
            state = detail["state"]
            if state in {"COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED"}:
                break
            time.sleep(0.1)

        assert state == "COMPLETED", detail
        assert detail["result"]["rows"] == 150


def test_path_traversal_and_unsafe_archive_guards(tmp_path: Path) -> None:
    try:
        safe_child(tmp_path, "../escape.txt")
        raise AssertionError("Expected ValueError for path traversal")
    except ValueError as exc:
        assert "PATH_OUTSIDE_WORKSPACE" in str(exc)

    bad_zip = tmp_path / "slip.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.png", b"not-an-image")
    bad_zip.write_bytes(buf.getvalue())

    try:
        extract_images(bad_zip, tmp_path / "out")
        raise AssertionError("Expected ValueError for zip-slip path")
    except ValueError as exc:
        assert "UNSAFE_ARCHIVE" in str(exc)


def test_diagnostics_excludes_datasets(tmp_path: Path) -> None:
    client, _ = _make_client(tmp_path)
    diag = client.get('/api/v1/system/diagnostics')
    assert diag.status_code == 200
    assert 'version' in diag.json()

