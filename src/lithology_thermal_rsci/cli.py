from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .data_validation import InputValidationError
from .pipeline import run_pipeline


def _repository_path(raw: str, root: Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else root / path


def _workflow_root(config_path: Path) -> Path:
    """Resolve relative run paths from the active repository checkout."""
    current = Path.cwd()
    if (current / "config").is_dir():
        return current
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return current


def run_from_config(config_path: str | Path) -> dict[str, Path]:
    requested = Path(config_path).resolve()
    root = _workflow_root(requested)
    cfg = load_config(requested)
    analysis = cfg.get("analysis", {})
    validation = cfg.get("validation", {})
    grid_size = analysis.get("grid_size")
    return run_pipeline(
        input_path=_repository_path(str(cfg["input"]["path"]), root),
        output_dir=_repository_path(str(cfg["output"]["directory"]), root),
        families=analysis.get("families", ["SVR", "GAM", "RF", "XGB"]),
        variants=analysis.get("variants", ["BASE", "SMOOTH", "INTERMEDIATE"]),
        include_tuned=bool(analysis.get("include_tuned", False)),
        tune_missing=bool(analysis.get("tune_missing", True)),
        grid_size=None if grid_size is None else int(grid_size),
        validation_options={
            "min_records_per_lithology": int(
                validation.get("min_records_per_lithology", 10)
            ),
            "density_identity_abs_tolerance_mg_m3": float(
                validation.get("density_identity_abs_tolerance_mg_m3", 0.02)
            ),
            "density_identity_rel_tolerance": float(
                validation.get("density_identity_rel_tolerance", 0.02)
            ),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the lithology-specific material-state, grouped-validation, and RSCI workflow."
        )
    )
    parser.add_argument(
        "--config", default="config/example_config.yml", help="YAML or JSON run configuration."
    )
    arguments = parser.parse_args()
    try:
        outputs = run_from_config(arguments.config)
    except (InputValidationError, FileNotFoundError, KeyError, ValueError) as error:
        raise SystemExit(f"Input/configuration error: {error}") from None
    for name, path in outputs.items():
        print(f"{name}: {Path(path).resolve()}")
