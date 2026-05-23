import argparse
import re
from typing import Any

from lib.api import ApiClient
from lib.models import CollectionRef
from lib.utils import first_value, parse_csv, value_as_string


def discover_collections(client: ApiClient, args: argparse.Namespace) -> list[CollectionRef]:
    """
    Discovers collection references.
    Called by: lib.sampler.run_sampler_with_client()
    """
    collection_pids = parse_csv(args.collection_pids)
    if collection_pids:
        collections = [CollectionRef(pid=pid, name=pid) for pid in collection_pids]
    elif args.collection_query_mode == 'search':
        collections = discover_collections_from_search(client)
    else:
        collections = discover_collections_from_endpoint(client)
        if not collections:
            collections = discover_collections_from_search(client)
    skip_pids = set(parse_csv(args.skip_collections))
    filtered = [collection for collection in collections if collection.pid not in skip_pids]
    return filtered


def discover_collections_from_endpoint(client: ApiClient) -> list[CollectionRef]:
    """
    Discovers collection references from the Collection API endpoint.
    Called by: discover_collections()
    """
    data = client.get_collections()
    candidates = extract_collection_entries(data)
    collections = []
    for entry in candidates:
        pid = extract_pid(entry)
        if pid:
            collections.append(CollectionRef(pid=pid, name=extract_title(entry, pid)))
    collections = unique_collections(collections)
    return collections


def discover_collections_from_search(client: ApiClient) -> list[CollectionRef]:
    """
    Discovers collection references from the Search API.
    Called by: discover_collections()
    """
    params = {
        'q': 'object_type:bdr-collection AND -rel_is_member_of_collection_ssim:*',
        'fl': 'pid,primary_title,collection_name_ssim',
        'rows': 500,
        'start': 0,
    }
    data = client.search(params)
    docs = solr_docs(data)
    collections = []
    for doc in docs:
        pid = value_as_string(doc.get('pid'))
        if pid:
            collections.append(CollectionRef(pid=pid, name=extract_title(doc, pid)))
    return collections


def count_top_level_items(client: ApiClient, collection_pid: str) -> int:
    """
    Counts top-level non-collection items in one collection.
    Called by: lib.sampler.run_sampler_with_client()
    """
    params = {
        'q': f'rel_is_member_of_collection_ssim:"{collection_pid}" AND -rel_is_part_of_ssim:* AND -object_type:bdr-collection',
        'fl': 'pid',
        'rows': 0,
    }
    data = client.search(params)
    count = solr_num_found(data)
    return count


def extract_collection_entries(data: Any) -> list[dict[str, Any]]:
    """
    Extracts collection dictionaries from common API response shapes.
    Called by: discover_collections_from_endpoint()
    """
    entries: list[dict[str, Any]] = []
    if isinstance(data, list):
        entries = [entry for entry in data if isinstance(entry, dict)]
    elif isinstance(data, dict):
        for key in ['collections', 'results', 'items', 'docs']:
            value = data.get(key)
            if isinstance(value, list):
                entries = [entry for entry in value if isinstance(entry, dict)]
                break
        if not entries and isinstance(data.get('response'), dict):
            entries = solr_docs(data)
    return entries


def extract_pid(entry: dict[str, Any]) -> str:
    """
    Extracts a PID from a collection-like API entry.
    Called by: discover_collections_from_endpoint()
    """
    pid = ''
    for key in ['pid', 'id', 'identifier']:
        value = entry.get(key)
        if value:
            pid = value_as_string(value)
            break
    if not pid:
        url = value_as_string(entry.get('url') or entry.get('href') or entry.get('api_url'))
        match = re.search(r'(bdr:[A-Za-z0-9_\-]+)', url)
        if match:
            pid = match.group(1)
    return pid


def extract_title(entry: dict[str, Any], fallback: str) -> str:
    """
    Extracts a display title from an API entry.
    Called by: discover_collections_from_endpoint()
    """
    title = fallback
    for key in ['name', 'title', 'primary_title', 'collection_name_ssim']:
        value = entry.get(key)
        if value:
            title = first_value(value)
            break
    return title


def unique_collections(collections: list[CollectionRef]) -> list[CollectionRef]:
    """
    Removes duplicate collections by PID.
    Called by: discover_collections_from_endpoint()
    """
    seen = set()
    unique = []
    for collection in collections:
        if collection.pid not in seen:
            unique.append(collection)
            seen.add(collection.pid)
    return unique


def solr_docs(data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extracts Solr docs from a Search API response.
    Called by: discover_collections_from_search()
    """
    response = data.get('response', {})
    docs = response.get('docs', []) if isinstance(response, dict) else []
    if not isinstance(docs, list):
        docs = []
    return docs


def solr_num_found(data: dict[str, Any]) -> int:
    """
    Extracts numFound from a Search API response.
    Called by: count_top_level_items()
    """
    response = data.get('response', {})
    num_found = response.get('numFound', 0) if isinstance(response, dict) else 0
    return int(num_found)


def select_collections(collections: list[CollectionRef], args: argparse.Namespace) -> list[CollectionRef]:
    """
    Selects the largest collections for analysis.
    Called by: lib.sampler.run_sampler_with_client()
    """
    selected = sorted(collections, key=lambda collection: collection.top_level_item_count, reverse=True)
    selected = selected[: args.max_collections]
    return selected


def collection_to_dict(collection: CollectionRef) -> dict[str, Any]:
    """
    Converts a collection reference to JSON data.
    Called by: lib.sampler.run_sampler_with_client()
    """
    data = {'pid': collection.pid, 'name': collection.name, 'top_level_item_count': collection.top_level_item_count}
    return data
