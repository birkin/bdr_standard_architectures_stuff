#!/usr/bin/env python
import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.api import ApiClient  # noqa: E402
from lib.cache import Cache  # noqa: E402
from lib.config import (  # noqa: E402
    DEFAULT_API_ROOT,
    DEFAULT_CACHE_DIR,
    DEFAULT_SLEEP_SECONDS,
    DEFAULT_SPECIFICATIONS_DIR,
    DEFAULT_USER_AGENT,
)
from lib.signatures import build_object_definition_signature, build_signature_entry  # noqa: E402
from lib.utils import first_value, write_json  # noqa: E402


OBJECT_DEFINITION_FIELDS = [
    'pid',
    'primary_title',
    'object_type',
    'mods_type_of_resource',
    'datastreams_ssi',
    'rel_has_part_ssim',
    'rel_is_part_of_ssim',
    'rel_has_pagination_ssim',
]


def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments.
    Called by: main()
    """
    parser = argparse.ArgumentParser(description='Get the object-definition signature for one BDR item.')
    parser.add_argument('pid', help='BDR item PID, such as bdr:123456.')
    parser.add_argument('--api-root', default=DEFAULT_API_ROOT)
    parser.add_argument('--cache-dir', default=DEFAULT_CACHE_DIR)
    parser.add_argument('--refresh-cache', action='store_true')
    parser.add_argument('--sleep-seconds', type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument('--specifications-dir', default=DEFAULT_SPECIFICATIONS_DIR)
    parser.add_argument('--compare-specifications', action='store_true')
    parser.add_argument('--output-json', default='', help='Optional path to write the JSON result.')
    args = parser.parse_args()
    return args


def main() -> None:
    """
    Runs the single-item object-definition signature CLI.
    Called by: module guard
    """
    args = parse_args()
    result = build_result(args)
    if args.output_json:
        write_json(Path(args.output_json), result)
    print(json.dumps(result, indent=2, sort_keys=True))


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    """
    Builds the output payload for one BDR item.
    Called by: main()
    """
    client = build_client(args)
    try:
        doc = fetch_item_doc(client, args.pid)
    finally:
        client.close()
    signature = build_object_definition_signature(
        doc,
        has_parent=has_field_value(doc, 'rel_is_part_of_ssim'),
        has_children=has_field_value(doc, 'rel_has_part_ssim'),
        is_ordered=has_field_value(doc, 'rel_has_pagination_ssim'),
    )
    entry = build_signature_entry('object_definition', signature, first_value(doc.get('pid')) or args.pid)
    entry.pop('observed_count', None)
    result = {
        'api_root': args.api_root,
        'pid': first_value(doc.get('pid')) or args.pid,
        'title': first_value(doc.get('primary_title')),
        'signature_entry': entry,
    }
    if args.compare_specifications:
        result['specification_match'] = find_specification_match(Path(args.specifications_dir), entry['signature_hash'])
    return result


def build_client(args: argparse.Namespace) -> ApiClient:
    """
    Builds an API client for the single-item lookup.
    Called by: build_result()
    """
    headers = {'User-Agent': DEFAULT_USER_AGENT}
    timeout = httpx.Timeout(60.0, connect=5.0)
    cache = Cache(Path(args.cache_dir), refresh_cache=args.refresh_cache)
    client = ApiClient(args.api_root, args.sleep_seconds, cache, httpx.Client(timeout=timeout, headers=headers))
    return client


def fetch_item_doc(client: ApiClient, pid: str) -> dict[str, Any]:
    """
    Fetches one BDR item document from the Search API.
    Called by: build_result()
    """
    params = {
        'q': f'pid:"{escape_solr_phrase(pid)}"',
        'fl': ','.join(OBJECT_DEFINITION_FIELDS),
        'rows': 1,
        'start': 0,
    }
    data = client.search(params)
    docs = data.get('response', {}).get('docs', [])
    if not docs:
        raise SystemExit(f'No Search API document found for {pid}')
    doc = docs[0]
    if not isinstance(doc, dict):
        raise SystemExit(f'Search API returned an invalid document for {pid}')
    return doc


def escape_solr_phrase(value: str) -> str:
    """
    Escapes a value for use inside a quoted Solr phrase.
    Called by: fetch_item_doc()
    """
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return escaped


def has_field_value(doc: dict[str, Any], field_name: str) -> bool:
    """
    Returns whether a Search API document field contains a meaningful value.
    Called by: build_result()
    """
    value = doc.get(field_name)
    if isinstance(value, list):
        has_value = any(item is not None and str(item) != '' for item in value)
    else:
        has_value = value is not None and str(value) != ''
    return has_value


def find_specification_match(specifications_dir: Path, signature_hash: str) -> dict[str, Any]:
    """
    Finds a matching object-definition specification entry.
    Called by: build_result()
    """
    path = specifications_dir / 'object_definition_signatures.yaml'
    relative_path = relative_display_path(path)
    match = {
        'matched': False,
        'path': str(path),
        'relative_path': relative_path,
        'message': '',
        'entry_key': '',
        'label': '',
        'description': '',
    }
    if path.exists():
        document = read_yaml(path)
        signatures = document.get('signatures', {})
        if isinstance(signatures, dict):
            match = find_signature_hash_match(signatures, signature_hash, path)
    else:
        match['message'] = f'Comparison file could not be found at {relative_path}.'
    return match


def relative_display_path(path: Path) -> str:
    """
    Builds a readable path relative to the current working directory when possible.
    Called by: find_specification_match()
    """
    try:
        display_path = str(path.relative_to(Path.cwd()))
    except ValueError:
        display_path = str(path)
    return display_path


def read_yaml(path: Path) -> dict[str, Any]:
    """
    Reads a YAML document.
    Called by: find_specification_match()
    """
    with path.open('r', encoding='utf-8') as file_object:
        loaded = yaml.safe_load(file_object)
    document = loaded if isinstance(loaded, dict) else {}
    return document


def find_signature_hash_match(signatures: dict[str, Any], signature_hash: str, path: Path) -> dict[str, Any]:
    """
    Finds a signature entry by hash.
    Called by: find_specification_match()
    """
    match = {
        'matched': False,
        'path': str(path),
        'relative_path': relative_display_path(path),
        'message': '',
        'entry_key': '',
        'label': '',
        'description': '',
    }
    for entry_key, entry in sorted(signatures.items()):
        if isinstance(entry, dict) and entry.get('signature_hash') == signature_hash:
            match = {
                'matched': True,
                'path': str(path),
                'relative_path': relative_display_path(path),
                'message': '',
                'entry_key': entry_key,
                'label': str(entry.get('label', '')),
                'description': str(entry.get('description', '')),
            }
            break
    return match


if __name__ == '__main__':
    main()
