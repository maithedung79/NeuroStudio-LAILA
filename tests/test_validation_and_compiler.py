"""Tests for graph validation rules, shape inference, leakage guards, and codegen."""

import ast
from pathlib import Path

import pytest

from neurostudio.compiler import compile_project
from neurostudio.core.schema import Project
from neurostudio.core.templates import template
from neurostudio.core.validation import GraphError, validate


def test_templates_validate_and_compile_syntax(tmp_path: Path) -> None:
    for idx, name in enumerate(["iris", "iris_rf", "iris_svm", "iris_pca", "regression", "diabetes_forest", "cifar10"]):
        project = template(name)
        report = validate(project)
        assert report["ok"], f"{name} failed validation: {report['errors']}"

        out_dir = tmp_path / f"compiled_{idx}_{name}"
        spec = compile_project(project, out_dir)
        assert spec["codegen_version"]
        for py_file in ["model.py", "runtime.py", "train.py", "evaluate.py", "inference.py"]:
            source = (out_dir / py_file).read_text(encoding="utf-8")
            ast.parse(source)


def test_cifar10_shape_inference_and_parameter_count() -> None:
    project = template("cifar10")
    report = validate(project)
    assert report["ok"]
    # Conv2D(3->16, 3x3, bias) = 448; Linear(16->10, bias) = 170 => 618 params.
    assert report["parameters"] == 618
    assert report["inferred"]["n0"]["shape"] == ["B", 3, 32, 32]
    assert report["inferred"]["n7"]["shape"] == ["B", 10]


def test_data_graph_rejects_preprocessing_before_split() -> None:
    raw = template("iris").model_dump()
    data_graph = next(g for g in raw["graphs"] if g["kind"] == "data")
    # Put StandardScaler before Split: Dataset(n0) -> StandardScaler(n2) -> Split(n1) -> ...
    data_graph["edges"] = [
        {"source": "n0", "target": "n2"},
        {"source": "n2", "target": "n1"},
        {"source": "n1", "target": "n3"},
        {"source": "n3", "target": "n4"},
    ]
    report = validate(Project.model_validate(raw))
    assert not report["ok"]
    assert any(err["code"] == "LEAKAGE" for err in report["errors"])


def test_model_graph_rejects_cycle_and_softmax_before_output() -> None:
    raw = template("cifar10").model_dump()
    model_graph = next(g for g in raw["graphs"] if g["kind"] == "model")
    # Replace Flatten/Linear/Output tail check: insert Softmax right before Output.
    nodes = model_graph["nodes"]
    output_node = nodes[-1]
    linear_node = nodes[-2]
    softmax_node = {"id": "n_soft", "type": "Softmax", "version": 1, "params": {"dim": 1}, "position": {"x": 0, "y": 0}}
    nodes.insert(-1, softmax_node)
    model_graph["edges"] = [e for e in model_graph["edges"] if e["target"] != output_node["id"]]
    model_graph["edges"].extend([
        {"source": linear_node["id"], "target": "n_soft"},
        {"source": "n_soft", "target": output_node["id"]},
    ])

    report = validate(Project.model_validate(raw))
    assert not report["ok"]
    assert any(err["code"] == "LOSS_HEAD" for err in report["errors"])

    # Introduce a cycle back from n2 (ReLU) to n1 (Conv2D).
    raw_cycle = template("cifar10").model_dump()
    cg = next(g for g in raw_cycle["graphs"] if g["kind"] == "model")
    cg["edges"].append({"source": "n2", "target": "n1"})
    cycle_report = validate(Project.model_validate(raw_cycle))
    assert not cycle_report["ok"]
    assert any(err["code"] == "CYCLE" for err in cycle_report["errors"])

    with pytest.raises(GraphError):
        compile_project(Project.model_validate(raw_cycle), Path("unused"))
