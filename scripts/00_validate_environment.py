from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path

from lithology_thermal_rsci import __version__
from lithology_thermal_rsci.config import load_json
from lithology_thermal_rsci.constants import LITHOLOGIES, MODEL_FAMILIES, MODEL_VARIANTS
from lithology_thermal_rsci.data_validation import read_table, validate_and_prepare
from lithology_thermal_rsci.state_aggregation import aggregate_material_states

ROOT = Path(__file__).resolve().parents[1]


def locked_versions() -> dict[str, str]:
    result = {}
    for raw_line in (ROOT / 'requirements-lock.txt').read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if line and not line.startswith('#'):
            name, version = line.split('==', 1)
            result[name] = version
    return result


def check_environment(strict_lock: bool = False) -> dict[str, object]:
    failures, warnings, actual_versions = [], [], {}
    for dist, pinned in locked_versions().items():
        try:
            actual = importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            if strict_lock or dist not in {'pytest', 'pytest-cov'}:
                failures.append(f'missing dependency: {dist} (reference pin {pinned})')
            else:
                warnings.append(f'missing optional development dependency: {dist}')
            continue
        actual_versions[dist] = actual
        if actual != pinned:
            (failures if strict_lock else warnings).append(
                f'{dist}: installed {actual}, reference pin {pinned}'
            )

    if __version__ != '2.0.1':
        failures.append(f'expected source version 2.0.1, got {__version__}')
    model_config = load_json('config/model_variants.json')
    if tuple(model_config['families']) != MODEL_FAMILIES:
        failures.append('model families differ from frozen configuration')
    if tuple(model_config['variants']) != MODEL_VARIANTS:
        failures.append('model variants differ from frozen configuration')
    tuning = load_json('config/tuning_search_spaces.json')
    if tuning['outer_cross_validation_folds'] != 5 or tuning['inner_cross_validation_folds'] != 3:
        failures.append('grouped CV must be 5 outer / 3 inner folds')
    if tuning['tuning_criterion'] != 'RMSE':
        failures.append('TUNED CV metric must be RMSE')
    rsci = load_json('config/rsci_definition.json')
    expected_weights = {
        'bounds_score': 0.20,
        'smoothness_score': 0.25,
        'extrema_score': 0.20,
        'gradient_stability_score': 0.20,
        'fragmentation_score': 0.15,
    }
    if rsci['weights'] != expected_weights or abs(sum(rsci['weights'].values()) - 1.0) > 1e-15:
        failures.append('RSCI weights differ from canonical definition')
    if rsci['output_scale'] != [0, 100]:
        failures.append('RSCI output scale differs from canonical definition')
    observations, _ = validate_and_prepare(read_table(ROOT / 'data/synthetic_example.csv'))
    states, report = aggregate_material_states(observations)
    synthetic = {
        'source_measurements': len(observations),
        'unique_material_states': len(states),
        'materials': int(states['material_id'].nunique()),
        'parent_materials': int(states['parent_material_id'].nunique()),
        'groups_per_lithology': states.groupby('lithology')['parent_material_id'].nunique().reindex(LITHOLOGIES).astype(int).to_dict(),
        'measurement_count_distribution': report.measurement_count_distribution,
    }
    expected = {
        'source_measurements': 256,
        'unique_material_states': 192,
        'materials': 96,
        'parent_materials': 48,
        'groups_per_lithology': {lithology: 12 for lithology in LITHOLOGIES},
        'measurement_count_distribution': {1: 128, 2: 64},
    }
    if synthetic != expected:
        failures.append(f'synthetic fixture has changed: {synthetic} != {expected}')
    return {
        'status': 'passed' if not failures else 'failed',
        'package_version': __version__,
        'strict_lock': strict_lock,
        'installed_versions': actual_versions,
        'synthetic_demonstration': synthetic,
        'warnings': warnings,
        'failures': failures,
    }


def main():
    parser = argparse.ArgumentParser(description='Core runtime and deterministic synthetic hierarchy check')
    parser.add_argument('--strict-lock', action='store_true', help='Require exact pinned versions including development dependencies')
    args = parser.parse_args()
    report = check_environment(strict_lock=args.strict_lock)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
