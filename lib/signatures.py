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
    child_groups = build_child_groups(child_docs, args.include_mime_types)
    signature = {
        'object_type': first_value(parent_doc.get('object_type')) or 'unknown',
        'datastreams': list(parse_datastreams(parent_doc, args.include_mime_types)),
        'child_count_bucket': count_bucket(len(child_docs)),
        'children_truncated': children_truncated,
        'child_groups': child_groups,
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
