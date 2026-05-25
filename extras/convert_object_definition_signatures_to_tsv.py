#!/usr/bin/env python
import csv
import json
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = PROJECT_ROOT / 'specifications' / 'object_definition_signatures.yaml'
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / 'TSVs' / 'object_definition_signatures.tsv'
FIELDNAMES = [
    'entry_key',
    'signature_hash',
    'label',
    'description',
    'observed_count',
    'exemplar_pids',
    'object_type',
    'typeOfResource',
    'has_parent',
    'has_children',
    'is_ordered',
    'datastream_ids',
    'datastream_details_json',
    'signature_json',
]


def main() -> None:
    """
    Converts object-definition signature YAML to TSV.
    Called by: module guard
    """
    document = read_yaml(DEFAULT_INPUT_PATH)
    rows = build_rows(document)
    write_tsv(DEFAULT_OUTPUT_PATH, rows)
    print(f'Wrote {len(rows)} rows to {DEFAULT_OUTPUT_PATH}')


def read_yaml(path: Path) -> dict[str, Any]:
    """
    Reads an object-definition signature YAML file.
    Called by: main()
    """
    with path.open('r', encoding='utf-8') as file_object:
        loaded = yaml.safe_load(file_object)
    document = loaded if isinstance(loaded, dict) else {}
    return document


def build_rows(document: dict[str, Any]) -> list[dict[str, str]]:
    """
    Builds TSV rows from a specification document.
    Called by: main()
    """
    signatures = document.get('signatures', {})
    rows = []
    if isinstance(signatures, dict):
        for entry_key, entry in sorted(signatures.items()):
            if isinstance(entry, dict):
                rows.append(build_row(entry_key, entry))
    return rows


def build_row(entry_key: str, entry: dict[str, Any]) -> dict[str, str]:
    """
    Builds one TSV row from one signature entry.
    Called by: build_rows()
    """
    signature = entry.get('signature', {})
    if not isinstance(signature, dict):
        signature = {}
    row = {
        'entry_key': entry_key,
        'signature_hash': string_value(entry.get('signature_hash')),
        'label': string_value(entry.get('label')),
        'description': string_value(entry.get('description')),
        'observed_count': string_value(entry.get('observed_count')),
        'exemplar_pids': pipe_join(entry.get('exemplar_pids')),
        'object_type': string_value(signature.get('object_type')),
        'typeOfResource': string_value(signature.get('typeOfResource')),
        'has_parent': string_value(signature.get('has_parent')),
        'has_children': string_value(signature.get('has_children')),
        'is_ordered': string_value(signature.get('is_ordered')),
        'datastream_ids': pipe_join(signature.get('datastream_ids')),
        'datastream_details_json': json_value(signature.get('datastream_details', [])),
        'signature_json': json_value(signature),
    }
    return row


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    """
    Writes rows to a TSV file.
    Called by: main()
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as file_object:
        writer = csv.DictWriter(file_object, fieldnames=FIELDNAMES, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def pipe_join(value: Any) -> str:
    """
    Formats a list-like value for one TSV cell.
    Called by: build_row()
    """
    if isinstance(value, list):
        text = '|'.join(string_value(item) for item in value)
    else:
        text = string_value(value)
    return text


def json_value(value: Any) -> str:
    """
    Formats structured values as deterministic JSON.
    Called by: build_row()
    """
    text = json.dumps(value, sort_keys=True, separators=(',', ':'))
    return text


def string_value(value: Any) -> str:
    """
    Converts scalar values to TSV-safe strings.
    Called by: build_row()
    """
    text = '' if value is None else str(value)
    return text


if __name__ == '__main__':
    main()
