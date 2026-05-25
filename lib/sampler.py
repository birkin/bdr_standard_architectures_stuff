import argparse
from pathlib import Path
from typing import Any

import httpx

from lib.api import ApiClient
from lib.cache import Cache
from lib.classification import classify_collection
from lib.collections import count_top_level_items, discover_collections, select_collections
from lib.config import DEFAULT_USER_AGENT
from lib.models import ArchitectureIndex
from lib.report import build_result
from lib.sampling import fetch_children, fetch_sampled_top_level_items
from lib.signatures import build_signature_bundle
from lib.specifications import write_specification_files
from lib.state import (
    collection_to_dict,
    ensure_checked_state,
    find_saved_collection,
    load_or_initialize_state,
    parent_check_key,
    save_state_if_enabled,
    update_saved_collection,
)
from lib.utils import value_as_string


def run_sampler(args: argparse.Namespace) -> dict[str, Any]:
    """
    Orchestrates discovery, sampling, classification, and reporting.
    Called by: main.main()
    """
    cache = Cache(Path(args.cache_dir), args.refresh_cache)
    timeout = httpx.Timeout(60.0, connect=5.0)
    headers = {'User-Agent': DEFAULT_USER_AGENT}
    client = ApiClient(args.api_root, args.sleep_seconds, cache, httpx.Client(timeout=timeout, headers=headers))
    state = load_or_initialize_state(args)
    try:
        result = run_sampler_with_client(args, client, state)
    finally:
        client.close()
    return result


def run_sampler_with_client(args: argparse.Namespace, client: ApiClient, state: dict[str, Any]) -> dict[str, Any]:
    """
    Runs sampler work using an injected API client.
    Called by: run_sampler()
    """
    collections = discover_collections(client, args)
    state['collections_discovered'] = [collection_to_dict(collection) for collection in collections]
    save_state_if_enabled(args, state)

    checked = ensure_checked_state(state)
    collection_by_pid = {collection.pid: collection for collection in collections}
    for collection in collections:
        if collection.pid in checked['collection_counts']:
            saved_collection = find_saved_collection(state, collection.pid)
            if saved_collection is not None:
                collection.top_level_item_count = int(saved_collection.get('top_level_item_count', 0))
            continue
        collection.top_level_item_count = count_top_level_items(client, collection.pid)
        checked['collection_counts'].append(collection.pid)
        update_saved_collection(state, collection)
        save_state_if_enabled(args, state)

    selected = select_collections(collections, args)
    state['selected_collections'] = [collection_to_dict(collection) for collection in selected]
    save_state_if_enabled(args, state)

    architecture_index = ArchitectureIndex.from_state(state)
    collection_summaries = state.setdefault('collection_summaries', [])
    parent_results = state.setdefault('parent_item_signature_results', {})

    for collection in selected:
        if collection.pid in checked['collections']:
            continue
        state['in_progress'] = {'collection_pid': collection.pid, 'parent_pid': ''}
        parent_docs = fetch_sampled_top_level_items(client, collection.pid, args)
        item_signature_hashes: list[str] = []
        for parent_doc in parent_docs:
            parent_pid = value_as_string(parent_doc.get('pid'))
            parent_key = parent_check_key(collection.pid, parent_pid)
            state['in_progress'] = {'collection_pid': collection.pid, 'parent_pid': parent_pid}
            if parent_key in checked['parent_items']:
                item_signature_hashes.append(parent_results[parent_key]['composite_signature_hash'])
                continue
            child_result = fetch_children(client, parent_pid, args)
            child_evidence = child_result.__dict__
            bundle = build_signature_bundle(collection.pid, parent_doc, child_result.docs, child_evidence, len(parent_docs))
            signature_hash = bundle['composite']['signature_hash']
            architecture_index.add_bundle(bundle, collection, parent_doc)
            state['dimension_signature_candidates'] = architecture_index.dimension_candidates
            state['composite_architecture_candidates'] = architecture_index.composite_candidates
            item_signature_hashes.append(signature_hash)
            parent_results[parent_key] = {
                'composite_signature_hash': signature_hash,
                'dimension_hashes': bundle['composite']['component_hashes'],
                'observation': bundle['observation'],
            }
            checked['parent_items'].append(parent_key)
            save_state_if_enabled(args, state)
        summary = classify_collection(collection, item_signature_hashes, args)
        collection_summaries.append(summary)
        architecture_index.mark_collection_summary(summary)
        state['dimension_signature_candidates'] = architecture_index.dimension_candidates
        state['composite_architecture_candidates'] = architecture_index.composite_candidates
        checked['collections'].append(collection.pid)
        state['in_progress'] = {'collection_pid': '', 'parent_pid': ''}
        save_state_if_enabled(args, state)
        write_incremental_specifications(args, collection_summaries, architecture_index, collection_by_pid, state)

    result = build_result(args, collection_summaries, architecture_index, collection_by_pid, state)
    return result


def write_incremental_specifications(
    args: argparse.Namespace,
    collection_summaries: list[dict[str, Any]],
    architecture_index: ArchitectureIndex,
    collection_by_pid: dict[str, Any],
    state: dict[str, Any],
) -> None:
    """
    Writes specification YAML files after each completed collection.
    Called by: run_sampler_with_client()
    """
    result = build_result(args, collection_summaries, architecture_index, collection_by_pid, state)
    write_specification_files(Path(args.output_specifications_dir), result)
