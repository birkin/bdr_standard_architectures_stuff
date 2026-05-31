from pathlib import Path
from typing import Any

import yaml

from lib.config import SIGNATURE_ARCHITECTURE_VERSION


SPECIFICATION_FILES = {
    'parent_relationship': 'parent_relationship_signatures.yaml',
    'object_definition': 'object_definition_signatures.yaml',
    'open_access': 'open_access_signatures.yaml',
    'visibility': 'visibility_signatures.yaml',
    'auxiliary_relationships': 'auxiliary_relationships_signatures.yaml',
    'children': 'children_signatures.yaml',
    'composite_architecture': 'composite_architecture_signatures.yaml',
}
PRESERVED_LABEL_FIELDS = {'label', 'description', 'narrative', 'status', 'notes'}


def write_specification_files(output_dir: Path, result: dict[str, Any]) -> None:
    """
    Writes specification YAML files from sampler result data.
    Called by: main.main()
    """
    specs = build_specification_documents(result)
    output_dir.mkdir(parents=True, exist_ok=True)
    for signature_type, document in specs.items():
        path = output_dir / SPECIFICATION_FILES[signature_type]
        merged_document = merge_existing_document(path, document)
        validate_specification_document(merged_document)
        write_yaml_document(path, merged_document)


def build_specification_documents(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Builds specification documents grouped by signature type.
    Called by: write_specification_files()
    """
    documents = {}
    for signature_type in SPECIFICATION_FILES:
        entries = entries_for_signature_type(signature_type, result)
        document = {
            'schema_version': 1,
            'signature_architecture_version': SIGNATURE_ARCHITECTURE_VERSION,
            'api_root': result.get('api_root', ''),
            'signature_type': signature_type,
            'signatures': build_signature_map(entries),
        }
        documents[signature_type] = document
    return documents


def entries_for_signature_type(signature_type: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Returns result entries for one specification signature type.
    Called by: build_specification_documents()
    """
    if signature_type == 'composite_architecture':
        entries = result.get('specification_composite_architectures', result.get('composite_architectures', []))
    else:
        entries = list(result.get('dimension_signatures', {}).get(signature_type, {}).values())
    return entries


def build_signature_map(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Builds a YAML-friendly signature mapping.
    Called by: build_specification_documents()
    """
    signature_map = {}
    for entry in entries:
        key = signature_key(entry)
        signature_map[key] = {
            'signature_hash': entry.get('signature_hash', ''),
            'label': entry.get('label', ''),
            'description': entry.get('description', ''),
            'exemplar_pids': entry.get('exemplar_pids', []),
            'signature': entry.get('signature', {}),
        }
        if entry.get('component_hashes'):
            signature_map[key]['component_hashes'] = entry['component_hashes']
    return signature_map


def merge_existing_document(path: Path, new_document: dict[str, Any]) -> dict[str, Any]:
    """
    Merges a new specification document with a compatible existing file.
    Called by: write_specification_files()
    """
    existing_document = read_existing_document(path)
    if documents_are_merge_compatible(existing_document, new_document):
        merged_document = dict(new_document)
        merged_signatures = dict(existing_document.get('signatures', {}))
        existing_by_hash = signatures_by_hash(merged_signatures)
        for key, new_entry in new_document.get('signatures', {}).items():
            existing_key = existing_by_hash.get(new_entry.get('signature_hash'), key)
            existing_entry = merged_signatures.get(existing_key, {})
            merged_signatures[existing_key] = merge_signature_entry(existing_entry, new_entry)
        merged_document['signatures'] = merged_signatures
    else:
        merged_document = new_document
    return merged_document


def read_existing_document(path: Path) -> dict[str, Any]:
    """
    Reads an existing YAML specification document.
    Called by: merge_existing_document()
    """
    document: dict[str, Any] = {}
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding='utf-8'))
        if isinstance(loaded, dict):
            document = loaded
    return document


def documents_are_merge_compatible(existing_document: dict[str, Any], new_document: dict[str, Any]) -> bool:
    """
    Checks whether two specification documents can be merged.
    Called by: merge_existing_document()
    """
    compatible = bool(existing_document)
    if compatible:
        compatible = existing_document.get('api_root') == new_document.get('api_root')
    if compatible:
        compatible = existing_document.get('signature_architecture_version') == new_document.get(
            'signature_architecture_version'
        )
    if compatible:
        compatible = existing_document.get('signature_type') == new_document.get('signature_type')
    return compatible


def signatures_by_hash(signatures: dict[str, dict[str, Any]]) -> dict[str, str]:
    """
    Builds a reverse lookup from signature hash to YAML entry key.
    Called by: merge_existing_document()
    """
    lookup = {}
    for key, entry in signatures.items():
        signature_hash = entry.get('signature_hash')
        if signature_hash:
            lookup[signature_hash] = key
    return lookup


def merge_signature_entry(existing_entry: dict[str, Any], new_entry: dict[str, Any]) -> dict[str, Any]:
    """
    Merges one generated signature entry with an existing entry.
    Called by: merge_existing_document()
    """
    merged_entry = dict(new_entry)
    for field in PRESERVED_LABEL_FIELDS:
        if existing_entry.get(field):
            merged_entry[field] = existing_entry[field]
    merged_entry['exemplar_pids'] = merge_exemplar_pids(
        existing_entry.get('exemplar_pids', []), new_entry.get('exemplar_pids', [])
    )
    return merged_entry


def merge_exemplar_pids(existing_pids: list[str], new_pids: list[str]) -> list[str]:
    """
    Merges bounded exemplar PID lists.
    Called by: merge_signature_entry()
    """
    merged_pids = []
    for pid in [*existing_pids, *new_pids]:
        if pid and pid not in merged_pids and len(merged_pids) < 3:
            merged_pids.append(pid)
    return merged_pids


def validate_specification_document(document: dict[str, Any]) -> None:
    """
    Validates the structural shape of one specification document.
    Called by: write_specification_files()
    """
    required_keys = {'schema_version', 'signature_architecture_version', 'api_root', 'signature_type', 'signatures'}
    missing_keys = required_keys - set(document)
    if missing_keys:
        raise ValueError(f'Missing specification keys: {sorted(missing_keys)}')
    if document['signature_type'] not in SPECIFICATION_FILES:
        raise ValueError(f'Unknown signature_type: {document["signature_type"]}')
    if not isinstance(document['signatures'], dict):
        raise ValueError('Specification signatures must be a mapping.')
    for entry in document['signatures'].values():
        validate_signature_entry(entry)


def validate_signature_entry(entry: dict[str, Any]) -> None:
    """
    Validates one specification signature entry.
    Called by: validate_specification_document()
    """
    required_keys = {'signature_hash', 'label', 'description', 'exemplar_pids', 'signature'}
    missing_keys = required_keys - set(entry)
    if missing_keys:
        raise ValueError(f'Missing signature entry keys: {sorted(missing_keys)}')
    if not isinstance(entry['signature'], dict):
        raise ValueError('Signature entry signature must be a mapping.')


def write_yaml_document(path: Path, document: dict[str, Any]) -> None:
    """
    Writes one specification YAML document with merge-policy comments.
    Called by: write_specification_files()
    """
    comment = (
        '# Generated by bdr_object_architectures.\n'
        '# Merge policy: for the same api_root and signature_architecture_version, generated fields may be refreshed.\n'
        '# Label-like human review fields such as label, description, narrative, status, and notes are preserved.\n'
    )
    yaml_text = yaml.safe_dump(document, sort_keys=False, allow_unicode=False)
    path.write_text(comment + yaml_text, encoding='utf-8')


def signature_key(entry: dict[str, Any]) -> str:
    """
    Builds a stable YAML key for a signature entry.
    Called by: build_signature_map()
    """
    label = str(entry.get('label') or entry.get('signature_type') or 'signature')
    normalized_label = ''.join(character if character.isalnum() else '_' for character in label.lower())
    normalized_label = '_'.join(part for part in normalized_label.split('_') if part)
    key = f'{normalized_label}_{entry.get("signature_hash", "")}'
    return key
