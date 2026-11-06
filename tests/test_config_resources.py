import json
from pathlib import Path

from lithology_thermal_rsci.config import load_json
from lithology_thermal_rsci.rsci import RSCISettings


ROOT = Path(__file__).resolve().parents[1]


def test_packaged_and_repository_configs_match():
    resource_dir = ROOT / "src/lithology_thermal_rsci/resources"
    for name in ("model_variants.json", "tuning_search_spaces.json", "rsci_definition.json"):
        repository = json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))
        packaged = json.loads((resource_dir / name).read_text(encoding="utf-8"))
        assert repository == packaged
        assert load_json(f"config/{name}") == repository


def test_rsci_configuration_is_valid():
    settings = RSCISettings.from_mapping(load_json("config/rsci_definition.json"))
    settings.validate()
    assert settings.lambda_min == 0.0
    assert settings.lambda_max == 5.0
    assert sum(settings.resolved_weights().values()) == 1.0
