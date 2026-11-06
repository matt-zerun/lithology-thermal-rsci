from __future__ import annotations

import csv
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_IDENTIFIER_TABLES = {
    Path("data/synthetic_example.csv"),
    Path("data/input_schema.csv"),
    Path("data/templates/rsci_canonical_observations_template.csv"),
}
IDENTIFIER_COLUMNS = {
    "observation_id",
    "material_state_id",
    "material_id",
    "parent_material_id",
    "first_observation_id",
}
FORBIDDEN_SUFFIXES = {
    ".docx",
    ".env",
    ".joblib",
    ".pkl",
    ".pickle",
    ".whl",
    ".xlsx",
    ".xls",
    ".zip",
}
FORBIDDEN_NAME_FRAGMENTS = {
    "final_source_dataset",
    "state_level_modelling_dataset",
    "sample_to_material_group",
    "outer_fold_assignments",
    "oof_predictions",
    "inner_fold_audit",
    "decision_a",
    "_" + "r" + "3",
}
IGNORED_DIRECTORIES = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".ipynb_checkpoints",
    ".eggs",
    "__pycache__",
    "build",
    "dist",
}
TEXT_SUFFIXES = {".cff", ".csv", ".json", ".md", ".py", ".toml", ".txt", ".yml", ".yaml"}
FORBIDDEN_PUBLIC_PATTERNS = {
    "superseded source-observation count": re.compile(
        r"(?<![\d.])" + "2" + r"(?:,)?" + "340" + r"(?![\d.])"
    ),
    "internal milestone label": re.compile(r"\b" + "R" + "3" + r"\b", re.IGNORECASE),
    "internal audit label 01": re.compile(
        r"\b" + "A" + r"01(?:[–-]" + "A" + r"14)?\b", re.IGNORECASE
    ),
    "internal audit label 06": re.compile(r"\b" + "A" + r"06\b", re.IGNORECASE),
    "internal audit label 11": re.compile(
        r"\b" + "A" + r"11(?:[–-]" + "A" + r"13)?\b", re.IGNORECASE
    ),
    "internal audit label 12": re.compile(r"\b" + "A" + r"12\b", re.IGNORECASE),
    "working analysis label": re.compile(r"\b" + "re" + r"run\b", re.IGNORECASE),
    "working status label": re.compile(
        r"\b" + "provision" + r"al\b", re.IGNORECASE
    ),
    "assistant platform label": re.compile(
        r"\b" + "Chat" + r"GPT\b", re.IGNORECASE
    ),
}
ABSOLUTE_LOCAL_PATH_PATTERNS = {
    "workspace path": re.compile("/" + "workspace" + "/"),
    "home-directory path": re.compile(r"/(?:" + "home" + r"|Users)/[^/\s]+/"),
    "Windows user path": re.compile(r"[A-Za-z]:" + r"\\Users\\"),
}
INSTITUTIONAL_SAMPLE_ID = re.compile(r"\b[A-Z]{3}\d{3}[A-Z]\d{5}M\d{2}\b")


def verify_release_boundary(root: Path = ROOT) -> dict[str, object]:
    failures: list[str] = []
    checked_csv_files = 0
    checked_files = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(
            part in IGNORED_DIRECTORIES or part.endswith(".egg-info")
            for part in relative.parts
        ):
            continue
        if not path.is_file():
            continue
        checked_files += 1
        lower_name = path.name.lower()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or lower_name.endswith(".tar.gz"):
            failures.append(f"forbidden archive/build/data file: {relative}")
        for fragment in FORBIDDEN_NAME_FRAGMENTS:
            if fragment in lower_name:
                failures.append(f"restricted record-level artefact name: {relative}")

        if path.suffix.lower() in TEXT_SUFFIXES and path.name != "MANIFEST.sha256":
            content = path.read_text(encoding="utf-8", errors="ignore")
            for description, pattern in FORBIDDEN_PUBLIC_PATTERNS.items():
                if pattern.search(content):
                    failures.append(f"{description} in public text: {relative}")
            for description, pattern in ABSOLUTE_LOCAL_PATH_PATTERNS.items():
                if pattern.search(content):
                    failures.append(f"{description} in public text: {relative}")
            if relative != Path("data/synthetic_example.csv") and INSTITUTIONAL_SAMPLE_ID.search(content):
                failures.append(f"institutional sample identifier in public text: {relative}")

        if path.suffix.lower() != ".csv" or relative in ALLOWED_IDENTIFIER_TABLES:
            continue
        checked_csv_files += 1
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream), [])
        overlap = IDENTIFIER_COLUMNS & set(header)
        if overlap:
            failures.append(
                f"identifier columns {sorted(overlap)} in public CSV: {relative}"
            )

    for forbidden_tree in ('reference_outputs', 'publication_figures'):
        if (root / forbidden_tree).exists():
            failures.append(f'archival output tree must not be in GitHub: {forbidden_tree}')
    for omitted in ('src/lithology_thermal_rsci/publication_figures.py',
                    'src/lithology_thermal_rsci/figures.py',
                    'src/lithology_thermal_rsci/reference_outputs.py'):
        if (root / omitted).exists():
            failures.append(f'publication-only module must not be in GitHub: {omitted}')

    model_config = json.loads(
        (root / "config/model_variants.json").read_text(encoding="utf-8")
    )
    if model_config["families"] != ["SVR", "GAM", "RF", "XGB"]:
        failures.append("public model-family configuration is not exactly SVR/GAM/RF/XGB")
    if model_config["variants"] != ["BASE", "SMOOTH", "INTERMEDIATE", "TUNED"]:
        failures.append("public configuration does not contain exactly four candidate variants")


    report = {
        "status": "passed" if not failures else "failed",
        "release_root": root.name,
        "checked_files": checked_files,
        "checked_public_csv_files": checked_csv_files,
        "restricted_identifier_columns_outside_synthetic_schema": 0
        if not failures
        else None,
        "failures": failures,
    }
    return report


def main() -> None:
    report = verify_release_boundary()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
