"""Committed JSON Schema export (D-09/D-10; Pitfall 5).

Imports only from ``goldmasters_contracts`` — never from the API layer — so
the export cannot acquire an HTTP dependency. Each contract is exported with
``model_json_schema(mode="serialization")``: the default ``validation`` mode
emits ``anyOf[number,string]`` for a ``Decimal``, which is the wrong wire form.
Output is canonicalised (sorted keys, LF endings, trailing newline) so the
drift test in plan 04 can byte-compare.

Plan 11 extends the ``CONTRACTS`` enumeration without restructuring the writer.
"""

from __future__ import annotations

import json
from pathlib import Path

from goldmasters_contracts.envelope import Envelope

__all__ = ["CONTRACTS", "canonicalise", "export_schema", "main"]

#: Contract enumeration: (schema file stem, model). Plan 11 appends the
#: remaining contracts here; the writer needs no other change.
CONTRACTS: tuple[tuple[str, type], ...] = (("envelope", Envelope),)


def canonicalise(payload: dict[str, object]) -> str:
    """Render canonical JSON: sorted keys, LF endings, trailing newline."""
    return json.dumps(payload, sort_keys=True, indent=2).replace("\r\n", "\n") + "\n"


def export_schema(
    output_dir: Path | str = Path(__file__).parent / "schema",
) -> list[Path]:
    """Export every contract in ``CONTRACTS`` to ``<output_dir>/<stem>.json``."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for stem, model in CONTRACTS:
        schema = model.model_json_schema(mode="serialization")  # type: ignore[attr-defined]
        target = out / f"{stem}.json"
        target.write_text(canonicalise(schema), encoding="utf-8", newline="\n")
        written.append(target)
    return written


def main() -> None:
    for target in export_schema():
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
