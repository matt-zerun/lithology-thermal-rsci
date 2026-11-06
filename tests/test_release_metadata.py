"""Metadata tests for the curated code-only snapshot, not Zenodo deposition."""
from pathlib import Path
import tomllib
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_citation_and_project_metadata():
    cff = yaml.safe_load((ROOT / 'CITATION.cff').read_text(encoding='utf-8'))
    assert cff['license'] == 'MIT'
    assert cff['version'] == '2.0.1'
    assert cff['authors'] == [{
        'family-names': 'Żeruń',
        'given-names': 'Mateusz',
        'orcid': 'https://orcid.org/0000-0002-6824-5624',
        'affiliation': 'Polish Geological Institute – National Research Institute (PGI-NRI)',
    }]
    assert cff['identifiers'][0]['value'] == '10.5281/zenodo.21682909'
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']
    assert project['version'] == '2.0.1'
    assert project['authors'] == [{'name': 'Mateusz Żeruń'}]
    assert project['license'] == 'MIT'
    assert project['license-files'] == ['LICENSE']
    assert not any(dep.startswith('matplotlib') or dep.startswith('pillow') for dep in project['dependencies'])


def test_rights_and_repo_scope():
    license_text = (ROOT / 'LICENSE').read_text(encoding='utf-8')
    assert 'Copyright (c) 2026 Mateusz Żeruń' in license_text
    assert 'Copyright (c) 2026 Państwowy Instytut' not in license_text
    assert not (ROOT / '.zenodo.json').exists()
    assert not (ROOT / 'reference_outputs').exists()
    readme = (ROOT / 'README.md').read_text(encoding='utf-8').lower()
    assert 'code-only' in readme
    assert 'zenodo' in readme


def test_public_input_schema_includes_required_and_optional_fields():
    schema = (ROOT / 'data/input_schema.csv').read_text(encoding='utf-8')
    for field in ('observation_id', 'material_id', 'parent_material_id',
                  'lithology', 'water_content_pct', 'bulk_density_mg_m3',
                  'thermal_conductivity_w_mk', 'source', 'data_origin',
                  'measurement_temperature_c', 'dry_density_mg_m3',
                  'particle_density_mg_m3'):
        assert f'\n{field},' in f'\n{schema}'
