from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml


def repository_root() -> Path:
    """Return the source-repository root when running from a checkout."""
    return Path(__file__).resolve().parents[2]


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON configuration from an explicit path, the repository, or package resources."""
    requested = Path(path)
    candidates: list[Path] = []
    if requested.is_absolute():
        candidates.append(requested)
    else:
        candidates.extend((Path.cwd() / requested, repository_root() / requested))

    for candidate in candidates:
        if candidate.is_file():
            with candidate.open("r", encoding="utf-8") as handle:
                return json.load(handle)

    resource = files("lithology_thermal_rsci").joinpath("resources", requested.name)
    if resource.is_file():
        with resource.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    searched = ", ".join(str(item) for item in candidates)
    raise FileNotFoundError(f"Configuration file not found: {path}. Searched: {searched} and package resources.")


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a top-level YAML or JSON run configuration from an explicit path."""
    requested = Path(path)
    if not requested.is_file():
        candidate = repository_root() / requested
        if not candidate.is_file():
            raise FileNotFoundError(f"Run configuration not found: {path}")
        requested = candidate
    suffix = requested.suffix.lower()
    with requested.open("r", encoding="utf-8") as handle:
        if suffix in {".yml", ".yaml"}:
            payload = yaml.safe_load(handle)
        elif suffix == ".json":
            payload = json.load(handle)
        else:
            raise ValueError(
                f"Unsupported run-configuration format: {suffix}. Use YAML or JSON."
            )
    if not isinstance(payload, dict):
        raise ValueError("The run-configuration root must be a mapping/object.")
    return payload
