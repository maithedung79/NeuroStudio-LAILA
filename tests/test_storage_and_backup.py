"""Tests for SQLite Store persistence, idempotency, and workspace backup/restore."""

from pathlib import Path

import pytest

from neurostudio.backup import backup_workspace, restore_workspace
from neurostudio.core.templates import template
from neurostudio.storage import Conflict, Store


def test_store_enqueue_idempotency_and_claim(tmp_path: Path) -> None:
    store = Store(tmp_path)
    proj = store.create(template("iris").model_dump())

    spec = {"project_revision": 1}
    j1 = store.enqueue("train", spec, project_id=proj["id"], key="run-key-1")
    j2 = store.enqueue("train", spec, project_id=proj["id"], key="run-key-1")
    assert j1["id"] == j2["id"]
    assert j1["state"] == "QUEUED"

    # Reusing an idempotency key with a different spec must fail with Conflict.
    with pytest.raises(Conflict, match="IDEMPOTENCY_CONFLICT"):
        store.enqueue("train", {"project_revision": 2}, project_id=proj["id"], key="run-key-1")

    assert store.claim(j1["id"]) is True
    assert store.claim(j1["id"]) is False
    assert store.cancel_queued(j1["id"]) is False

    j3 = store.enqueue("profile", {"dataset": {"id": "iris"}})
    assert store.cancel_queued(j3["id"]) is True
    assert store.job(j3["id"])["state"] == "CANCELLED"


def test_store_blocks_archive_when_job_active(tmp_path: Path) -> None:
    store = Store(tmp_path)
    proj = store.create(template("iris").model_dump())
    job = store.enqueue("train", {"ok": True}, project_id=proj["id"])

    with pytest.raises(Conflict):
        store.archive_project(proj["id"], proj["revision"])

    assert store.cancel_queued(job["id"]) is True
    archived = store.archive_project(proj["id"], proj["revision"])
    assert archived["archived"] is True


def test_workspace_backup_and_restore_remap(tmp_path: Path) -> None:
    source_root = tmp_path / "workspace-a"
    store = Store(source_root)
    proj = store.create(template("iris").model_dump())

    dataset_file = source_root / "datasets" / "ds1" / "data.csv"
    dataset_file.parent.mkdir(parents=True, exist_ok=True)
    dataset_file.write_text("a,b,target\n1,2,0\n", encoding="utf-8")
    store.save_dataset("ds1", {"id": "ds1", "kind": "csv", "path": str(dataset_file)})
    store.enqueue("profile", {"path": str(dataset_file)}, project_id=proj["id"])

    backup_zip = tmp_path / "backups" / "snapshot.zip"
    info = backup_workspace(source_root, backup_zip)
    assert Path(info["path"]).is_file()

    # Checksum mismatch and existing target must be rejected.
    with pytest.raises(ValueError, match="BACKUP_CHECKSUM_MISMATCH"):
        restore_workspace(backup_zip, tmp_path / "restored-bad", "0" * 64)

    with pytest.raises(ValueError, match="RESTORE_DESTINATION_EXISTS"):
        restore_workspace(backup_zip, source_root, info["sha256"])

    dest_root = tmp_path / "workspace-b"
    restored = restore_workspace(backup_zip, dest_root, info["sha256"])
    assert Path(restored["directory"]) == dest_root.resolve()

    restored_store = Store(dest_root)
    assert len(restored_store.projects()) == 1
    assert restored_store.dataset("ds1")["path"] == str((dest_root / "datasets" / "ds1" / "data.csv").resolve())
    assert restored_store.jobs()[0]["state"] == "INTERRUPTED"
