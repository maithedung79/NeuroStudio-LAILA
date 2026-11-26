"""End-to-end tests for sklearn training, holdout evaluation, CV, exploration, and export."""

from pathlib import Path

import pytest

from neurostudio.compiler import compile_project, export_run
from neurostudio.core.templates import template
from neurostudio.engine.exploration import run_exploration
from neurostudio.engine.portable import (
    audit_duplicate_splits,
    cross_validate_training,
    evaluate_holdout,
    inference,
    train,
)
from neurostudio.exploration_export import export_exploration


def test_sklearn_classification_end_to_end_and_export(tmp_path: Path) -> None:
    project = template("iris")
    run_dir = tmp_path / "runs" / "iris-cls"
    spec = compile_project(project, run_dir / "compiled-project")
    descriptor = {"kind": "iris", "hash": "sklearn-iris-v1"}

    val_result = train(spec, descriptor, run_dir)
    assert val_result["accuracy"] > 0.7
    assert (run_dir / "pipeline.joblib").is_file()

    test_result = evaluate_holdout(spec, descriptor, run_dir)
    assert test_result["split"] == "test"
    assert test_result["accuracy"] > 0.7

    preds = inference(run_dir)
    assert len(preds) == 1
    assert abs(sum(preds[0]["scores"]) - 1.0) < 1e-5

    export_dir = tmp_path / "exports" / "iris-cls"
    archive = export_run(run_dir, export_dir)
    assert archive.is_file()
    exported_preds = inference(export_dir / "artifacts")
    assert len(exported_preds) == 1


def test_sklearn_regression_and_cv_study(tmp_path: Path) -> None:
    project = template("regression")
    run_dir = tmp_path / "runs" / "diabetes-reg"
    spec = compile_project(project, run_dir / "compiled-project")
    descriptor = {"kind": "diabetes", "hash": "sklearn-diabetes-v1"}

    val_result = train(spec, descriptor, run_dir)
    assert val_result["task"] == "regression"
    assert val_result["rmse"] > 0

    preds = inference(run_dir)
    assert isinstance(preds[0]["value"], float)

    cv = cross_validate_training(spec, descriptor, folds=3)
    assert len(cv["folds"]) == 3
    assert "r2_mean" in cv


def test_duplicate_split_leakage_is_rejected() -> None:
    with pytest.raises(ValueError, match="DATA_LEAKAGE"):
        audit_duplicate_splits(["dup", "unique", "dup"], {"train": [0, 1], "validation": [2], "test": []})


def test_exploration_kmeans_pca_and_export(tmp_path: Path) -> None:
    run_dir = tmp_path / "exploration"
    result = run_exploration(
        {
            "dataset_id": "iris",
            "target": "target",
            "features": [],
            "method": "kmeans",
            "projection": "pca",
            "clusters": 3,
            "sample_limit": 150,
            "seed": 42,
        },
        {"kind": "iris"},
        run_dir,
    )
    assert result["metrics"]["clusters"] == 3
    assert len(result["points"]) == 150

    archive = export_exploration(run_dir, tmp_path / "exploration-export")
    assert archive.is_file()
