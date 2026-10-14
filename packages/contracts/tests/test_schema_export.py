"""Committed-schema drift tests (D-10; Pitfall 8).

Regenerates into a temp directory with the same entry point the gate runs
and byte-compares against the committed documents after CRLF normalisation,
so a Windows checkout cannot produce false drift.
"""

from __future__ import annotations

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO / "packages" / "contracts" / "schema"


def _load_exporter() -> object:
    path = REPO / "packages" / "contracts" / "_export_schema.py"
    spec = importlib.util.spec_from_file_location("gm_export_schema_drift", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalise(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n")


def test_committed_schema_matches_regenerated(tmp_path: pathlib.Path) -> None:
    exporter = _load_exporter()
    committed = sorted(SCHEMA_DIR.glob("*.json"))
    assert committed, "committed schema set is empty"
    exporter.export_schema(tmp_path)  # type: ignore[attr-defined]
    for document in committed:
        regenerated = tmp_path / document.name
        assert regenerated.is_file(), f"no regenerated document for {document.name}"
        assert _normalise(regenerated.read_bytes()) == _normalise(document.read_bytes()), (
            f"drift in {document.name}: re-run packages/contracts/_export_schema.py"
        )


def test_every_contract_has_a_committed_document() -> None:
    exporter = _load_exporter()
    enumerated = sorted(stem for stem, _ in exporter.CONTRACTS)  # type: ignore[attr-defined]
    committed = sorted(path.stem for path in SCHEMA_DIR.glob("*.json"))
    assert enumerated == committed


def test_decimal_fields_are_strings() -> None:
    import json

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            assert isinstance(node, dict)
            if "anyOf" in node:
                for branch in node["anyOf"]:
                    if branch.get("type") == "number":
                        assert path.startswith("sentiment.json/properties/score"), (
                            f"{path}: number union"
                        )
            if node.get("type") == "number":
                assert path.startswith("sentiment.json/properties/score"), (
                    f"{path}: number"
                )
            for key, value in node.items():
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    for document in sorted(SCHEMA_DIR.glob("*.json")):
        walk(json.loads(document.read_text(encoding="utf-8")), document.name)
