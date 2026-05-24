import argparse
import hashlib
import json
import logging
from typing import Any

from lib.utils import first_value

log = logging.getLogger(__name__)


def build_item_signature(
    parent_doc: dict[str, Any],
    child_docs: list[dict[str, Any]],
    args: argparse.Namespace,
    children_truncated: bool = False,
) -> dict[str, Any]:
    """
    Builds a stable architecture signature from one parent and its children.
    Called by: lib.sampler.run_sampler_with_client()
    """
    child_groups = build_child_groups(child_docs, True)
    signature = {
        'object_type': first_value(parent_doc.get('object_type')) or 'unknown',
        'datastreams': list(parse_datastreams(parent_doc, True)),
        'child_count_bucket': count_bucket(len(child_docs)),
        'child_groups': child_groups,
    }
    return signature


def build_signature_bundle(
    collection_pid: str,
    parent_doc: dict[str, Any],
    child_docs: list[dict[str, Any]],
    child_evidence: dict[str, Any],
    parent_sampled_count: int,
) -> dict[str, Any]:
    """
    Builds dimension and composite signatures from one parent observation.
    Called by: lib.sampler.run_sampler_with_client()
    """
    parent_pid = first_value(parent_doc.get('pid'))
    parent_relationship = build_signature_entry(
        'parent_relationship',
        build_parent_relationship_signature(child_docs),
        parent_pid,
    )
    parent_object_definition = build_signature_entry(
        'object_definition',
        build_object_definition_signature(parent_doc, has_parent=False, has_children=bool(child_docs), is_ordered=False),
        parent_pid,
    )
    child_object_definitions = build_child_object_definition_entries(child_docs)
    children = build_signature_entry(
        'children',
        build_children_signature(child_object_definitions),
        parent_pid,
    )
    open_access = build_signature_entry('open_access', build_open_access_signature(parent_doc, child_docs), parent_pid)
    visibility = build_signature_entry('visibility', build_visibility_signature(), parent_pid)
    auxiliary_relationships = build_signature_entry(
        'auxiliary_relationships',
        build_auxiliary_relationships_signature(parent_doc, child_docs),
        parent_pid,
    )
    component_hashes = {
        'parent_relationship': parent_relationship['signature_hash'],
        'parent_object_definition': parent_object_definition['signature_hash'],
        'children': children['signature_hash'],
        'open_access': open_access['signature_hash'],
        'visibility': visibility['signature_hash'],
        'auxiliary_relationships': auxiliary_relationships['signature_hash'],
    }
    composite_signature = {'component_hashes': component_hashes}
    composite = build_signature_entry('composite_architecture', composite_signature, parent_pid)
    composite['component_hashes'] = component_hashes
    composite['label'] = label_composite_signature(parent_object_definition, children)
    dimensions = {
        'parent_relationship': parent_relationship,
        'parent_object_definition': parent_object_definition,
        'child_object_definitions': child_object_definitions,
        'children': children,
        'open_access': open_access,
        'visibility': visibility,
        'auxiliary_relationships': auxiliary_relationships,
    }
    observation = {
        'collection_pid': collection_pid,
        'parent_pid': parent_pid,
        'parent_sampled_count': parent_sampled_count,
        'child_total_found': child_evidence.get('total_found', len(child_docs)),
        'child_observed_count': child_evidence.get('observed_count', len(child_docs)),
        'child_sample_limit': child_evidence.get('sample_limit', len(child_docs)),
        'child_hard_limit': child_evidence.get('hard_limit', 1000),
        'children_truncated': child_evidence.get('truncated', False),
        'fetch_all_children_max_1000': child_evidence.get('fetch_all_children_max_1000', False),
        'child_fetch_strategy': child_evidence.get('fetch_strategy', 'first_by_pid_then_bdr_child_sort'),
        'visibility_scope': 'public_api_observed',
    }
    bundle = {'observation': observation, 'dimensions': dimensions, 'composite': composite}
    return bundle


def build_signature_entry(signature_type: str, signature: dict[str, Any], exemplar_pid: str) -> dict[str, Any]:
    """
    Builds a metadata wrapper around one signature structure.
    Called by: build_signature_bundle()
    """
    signature_hash = hash_signature(signature)
    entry = {
        'signature_type': signature_type,
        'signature_hash': signature_hash,
        'label': label_dimension_signature(signature_type, signature),
        'description': describe_dimension_signature(signature_type, signature),
        'exemplar_pids': [exemplar_pid] if exemplar_pid else [],
        'observed_count': 1,
        'signature': signature,
    }
    return entry


def build_parent_relationship_signature(child_docs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Builds a parent relationship dimension signature.
    Called by: build_signature_bundle()
    """
    signature = {
        'has_children': bool(child_docs),
        'ordered_children': any(first_value(child_doc.get('rel_has_pagination_ssim')) for child_doc in child_docs),
    }
    return signature


def build_object_definition_signature(
    doc: dict[str, Any], has_parent: bool, has_children: bool, is_ordered: bool
) -> dict[str, Any]:
    """
    Builds an object definition dimension signature.
    Called by: build_signature_bundle()
    """
    datastream_details = parse_datastream_details(doc)
    signature = {
        'object_type': first_value(doc.get('object_type')) or 'unknown',
        'typeOfResource': first_value(doc.get('mods_type_of_resource')) or 'unknown',
        'has_parent': has_parent,
        'has_children': has_children,
        'is_ordered': is_ordered,
        'datastream_ids': [detail['id'] for detail in datastream_details],
        'datastream_details': datastream_details,
    }
    return signature


def build_child_object_definition_entries(child_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Builds object definition entries for observed child docs.
    Called by: build_signature_bundle()
    """
    entries_by_hash: dict[str, dict[str, Any]] = {}
    for child_doc in child_docs:
        child_pid = first_value(child_doc.get('pid'))
        is_ordered = bool(first_value(child_doc.get('rel_has_pagination_ssim')))
        signature = build_object_definition_signature(child_doc, has_parent=True, has_children=False, is_ordered=is_ordered)
        entry = build_signature_entry('object_definition', signature, child_pid)
        existing_entry = entries_by_hash.get(entry['signature_hash'])
        if existing_entry is None:
            entries_by_hash[entry['signature_hash']] = entry
        else:
            existing_entry['observed_count'] += 1
            append_exemplar_pid(existing_entry, child_pid)
    entries = sorted(entries_by_hash.values(), key=lambda item: item['signature_hash'])
    return entries


def build_children_signature(child_object_definitions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Builds a children dimension signature from unique child object definitions.
    Called by: build_signature_bundle()
    """
    signature = {
        'object_definition_hashes': sorted({entry['signature_hash'] for entry in child_object_definitions}),
    }
    return signature


def build_open_access_signature(parent_doc: dict[str, Any], child_docs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Builds an open access dimension signature from public API evidence.
    Called by: build_signature_bundle()
    """
    docs = [parent_doc, *child_docs]
    signature = {
        'license': first_known_values(
            docs,
            ['mods_access_condition_use_text_tsim', 'mods_access_condition_use_link_ssim'],
        ),
        'rights_statement': first_known_values(
            docs,
            ['mods_access_condition_rights_text_tsim', 'mods_access_condition_rights_link_ssim'],
        ),
        'restriction_statement': first_known_values(docs, ['mods_access_condition_restriction_text_tsim']),
        'access_control': {
            'public': observed_boolean_values(docs, '_display_public_bsi'),
            'brown': observed_boolean_values(docs, '_display_brown_bsi'),
            'private': observed_boolean_values(docs, '_display_private_bsi'),
        },
        'current_embargo_status': {
            'status': first_known_values(docs, ['rel_pso_status_ssi']),
            'years': first_known_values(docs, ['rel_embargo_years_ssim']),
            'computed_current_status': 'unknown',
        },
    }
    return signature


def build_visibility_signature() -> dict[str, Any]:
    """
    Builds a visibility dimension signature.
    Called by: build_signature_bundle()
    """
    signature = {'visibility_scope': 'public_api_observed'}
    return signature


def build_auxiliary_relationships_signature(parent_doc: dict[str, Any], child_docs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Builds an auxiliary relationships dimension signature.
    Called by: build_signature_bundle()
    """
    docs = [parent_doc, *child_docs]
    signature = {
        'has_derivations': any(has_value(doc, 'rel_is_derivation_of_ssim') for doc in docs),
        'has_transcripts': any(has_value(doc, 'rel_is_transcript_of_ssim') for doc in docs),
        'has_translations': any(has_value(doc, 'rel_is_translation_of_ssim') for doc in docs),
        'has_annotations': any(has_value(doc, 'rel_is_annotation_of_ssim') for doc in docs),
    }
    return signature


def build_child_groups(child_docs: list[dict[str, Any]], include_mime_types: bool) -> list[dict[str, Any]]:
    """
    Builds normalized child groups for a signature.
    Called by: build_item_signature()
    """
    grouped: dict[tuple[str, str, tuple[str, ...]], int] = {}
    for child_doc in child_docs:
        object_type = first_value(child_doc.get('object_type')) or 'unknown'
        display_label = first_value(child_doc.get('rel_display_label_ssi')) or ''
        datastreams = parse_datastreams(child_doc, include_mime_types)
        key = (object_type, display_label, datastreams)
        grouped[key] = grouped.get(key, 0) + 1
    groups = []
    for key, count in sorted(grouped.items(), key=lambda item: item[0]):
        object_type, display_label, datastreams = key
        groups.append(
            {
                'object_type': object_type,
                'display_label': display_label,
                'datastreams': list(datastreams),
                'count_bucket': count_bucket(count),
                'exact_count': count,
            }
        )
    return groups


def parse_datastreams(doc: dict[str, Any], include_mime_types: bool = False) -> tuple[str, ...]:
    """
    Parses datastream inventory from a Solr doc.
    Called by: build_item_signature()
    """
    raw_value = doc.get('datastreams_ssi')
    datastreams: list[str] = []
    if not raw_value:
        datastreams = []
    else:
        parsed_value = parse_datastreams_json(first_value(raw_value))
        if parsed_value is None:
            datastreams = ['__INVALID_DATASTREAMS_JSON__']
        else:
            datastreams = normalize_datastreams(parsed_value, include_mime_types)
    result = tuple(sorted(datastreams))
    return result


def parse_datastream_details(doc: dict[str, Any]) -> list[dict[str, str]]:
    """
    Parses datastream inventory into structured details.
    Called by: build_object_definition_signature()
    """
    raw_value = doc.get('datastreams_ssi')
    details: list[dict[str, str]] = []
    if raw_value:
        parsed_value = parse_datastreams_json(first_value(raw_value))
        if parsed_value is None:
            details = [{'id': '__INVALID_DATASTREAMS_JSON__', 'mime_type': 'unknown'}]
        else:
            details = normalize_datastream_details(parsed_value)
    details.sort(key=lambda item: (item['id'], item['mime_type']))
    return details


def parse_datastreams_json(raw_value: str) -> dict[str, Any] | None:
    """
    Parses datastream JSON safely.
    Called by: parse_datastreams()
    """
    parsed_value = None
    try:
        loaded = json.loads(raw_value)
        if isinstance(loaded, dict):
            parsed_value = loaded
    except json.JSONDecodeError:
        parsed_value = None
    return parsed_value


def normalize_datastreams(parsed_value: dict[str, Any], include_mime_types: bool) -> list[str]:
    """
    Normalizes parsed datastream JSON to stable tokens.
    Called by: parse_datastreams()
    """
    datastreams = []
    for datastream_id, metadata in parsed_value.items():
        token = str(datastream_id)
        if include_mime_types and isinstance(metadata, dict) and metadata.get('mimeType'):
            token = f'{token}:{metadata["mimeType"]}'
        datastreams.append(token)
    return datastreams


def normalize_datastream_details(parsed_value: dict[str, Any]) -> list[dict[str, str]]:
    """
    Normalizes parsed datastream JSON to structured details.
    Called by: parse_datastream_details()
    """
    details = []
    for datastream_id, metadata in parsed_value.items():
        mime_type = 'unknown'
        if isinstance(metadata, dict) and metadata.get('mimeType'):
            mime_type = str(metadata['mimeType'])
        details.append({'id': str(datastream_id), 'mime_type': mime_type})
    return details


def hash_signature(signature: dict[str, Any]) -> str:
    """
    Hashes a signature using deterministic JSON.
    Called by: lib.sampler.run_sampler_with_client()
    """
    signature_key = json.dumps(signature, sort_keys=True, separators=(',', ':'))
    log.debug(f'signature_key, ``{signature_key}``')
    signature_hash = hashlib.sha256(signature_key.encode('utf-8')).hexdigest()[:12]
    return signature_hash


def count_bucket(count: int) -> str:
    """
    Converts a count to the architecture bucket vocabulary.
    Called by: build_item_signature()
    """
    if count == 0:
        bucket = 'none'
    elif count == 1:
        bucket = 'one'
    elif count < 10:
        bucket = 'few:2-9'
    else:
        bucket = 'many:10+'
    return bucket


def label_signature(signature: dict[str, Any]) -> str:
    """
    Generates a human-friendly architecture label.
    Called by: lib.models.ArchitectureIndex.add()
    """
    object_type = signature.get('object_type', 'unknown')
    child_groups = signature.get('child_groups', [])
    if not child_groups:
        label = f'standalone {object_type}'
    elif len(child_groups) == 1:
        label = f'{object_type} with {child_groups[0].get("object_type", "unknown")} children'
    else:
        child_labels = [f'{group.get("object_type", "unknown")} children' for group in child_groups]
        label = f'{object_type} with {" plus ".join(child_labels)}'
    return label


def label_dimension_signature(signature_type: str, signature: dict[str, Any]) -> str:
    """
    Generates a human-friendly dimension signature label.
    Called by: build_signature_entry()
    """
    if signature_type == 'parent_relationship':
        if signature.get('ordered_children'):
            label = 'parent with ordered children'
        elif signature.get('has_children'):
            label = 'parent with children'
        else:
            label = 'standalone parent'
    elif signature_type == 'object_definition':
        label = f'{signature.get("object_type", "unknown")} object definition'
    elif signature_type == 'children':
        count = len(signature.get('object_definition_hashes', []))
        label = f'{count} child object definition type{"s" if count != 1 else ""}'
    elif signature_type == 'open_access':
        label = 'open access evidence'
    elif signature_type == 'visibility':
        label = signature.get('visibility_scope', 'visibility evidence')
    elif signature_type == 'auxiliary_relationships':
        label = 'auxiliary relationship evidence'
    elif signature_type == 'composite_architecture':
        label = 'composite architecture'
    else:
        label = signature_type.replace('_', ' ')
    return label


def label_composite_signature(parent_object_definition: dict[str, Any], children: dict[str, Any]) -> str:
    """
    Generates a human-friendly composite architecture label.
    Called by: build_signature_bundle()
    """
    parent_type = parent_object_definition.get('signature', {}).get('object_type', 'unknown')
    child_count = len(children.get('signature', {}).get('object_definition_hashes', []))
    if child_count:
        label = f'{parent_type} with {child_count} child definition type{"s" if child_count != 1 else ""}'
    else:
        label = f'standalone {parent_type}'
    return label


def describe_dimension_signature(signature_type: str, signature: dict[str, Any]) -> str:
    """
    Describes a dimension signature for review output.
    Called by: build_signature_entry()
    """
    label = label_dimension_signature(signature_type, signature)
    description = f'Observed {label} through public BDR API sampling.'
    return description


def append_exemplar_pid(entry: dict[str, Any], pid: str) -> None:
    """
    Appends a bounded exemplar PID to a signature entry.
    Called by: build_child_object_definition_entries()
    """
    exemplars = entry.setdefault('exemplar_pids', [])
    if pid and pid not in exemplars and len(exemplars) < 3:
        exemplars.append(pid)


def has_value(doc: dict[str, Any], key: str) -> bool:
    """
    Returns whether a document field has an observed value.
    Called by: build_auxiliary_relationships_signature()
    """
    value = doc.get(key)
    if isinstance(value, list):
        result = bool(value)
    else:
        result = bool(value)
    return result


def field_values(doc: dict[str, Any], key: str) -> list[str]:
    """
    Returns normalized string values for one field.
    Called by: first_known_values()
    """
    value = doc.get(key)
    if isinstance(value, list):
        values = [str(item) for item in value if item not in {None, ''}]
    elif value is None or value == '':
        values = []
    else:
        values = [str(value)]
    return values


def first_known_values(docs: list[dict[str, Any]], keys: list[str]) -> list[str] | str:
    """
    Collects stable observed values for a set of fields.
    Called by: build_open_access_signature()
    """
    values: list[str] = []
    for doc in docs:
        for key in keys:
            for value in field_values(doc, key):
                if value not in values:
                    values.append(value)
    result: list[str] | str = values if values else 'unknown'
    return result


def observed_boolean_values(docs: list[dict[str, Any]], key: str) -> list[str] | str:
    """
    Collects observed boolean-like values for access fields.
    Called by: build_open_access_signature()
    """
    result = first_known_values(docs, [key])
    return result
