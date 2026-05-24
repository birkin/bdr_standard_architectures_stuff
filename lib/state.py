import argparse
import json
from pathlib import Path
from typing import Any

from lib.config import SCRIPT_VERSION, SIGNATURE_ARCHITECTURE_VERSION
from lib.models import CollectionRef
from lib.utils import atomic_write_json, utc_now


def load_or_initialize_state(args: argparse.Namespace) -> dict[str, Any]:
    """
    Loads compatible state or initializes a new state object.
    Called by: lib.sampler.run_sampler()
    """
    state_path = Path(args.state_file)
    if args.no_resume or args.refresh_state or not state_path.exists():
        state = new_state(args)
    else:
        with state_path.open('r', encoding='utf-8') as file_object:
            state = json.load(file_object)
        validate_state_compatibility(state, args)
        ensure_checked_state(state)
        state.setdefault('parent_item_signature_results', {})
        state.setdefault('dimension_signature_candidates', {})
        state.setdefault('composite_architecture_candidates', {})
        state.setdefault('collection_summaries', [])
        state.setdefault('warnings', [])
    return state


def new_state(args: argparse.Namespace) -> dict[str, Any]:
    """
    Initializes a fresh resumable state object.
    Called by: load_or_initialize_state()
    """
    state = {
        'script_version': SCRIPT_VERSION,
        'signature_architecture_version': SIGNATURE_ARCHITECTURE_VERSION,
        'api_root': args.api_root,
        'parameters': material_parameters(args),
        'started_at': utc_now(),
        'updated_at': utc_now(),
        'collections_discovered': [],
        'selected_collections': [],
        'checked': {'collection_counts': [], 'collections': [], 'parent_items': []},
        'parent_item_signature_results': {},
        'in_progress': {'collection_pid': '', 'parent_pid': ''},
        'dimension_signature_candidates': {},
        'composite_architecture_candidates': {},
        'collection_summaries': [],
        'warnings': [],
    }
    return state


def validate_state_compatibility(state: dict[str, Any], args: argparse.Namespace) -> None:
    """
    Validates that saved state can be resumed by this run.
    Called by: load_or_initialize_state()
    """
    expected_parameters = material_parameters(args)
    if state.get('script_version') != SCRIPT_VERSION:
        raise ValueError('Saved state script_version does not match. Use --refresh-state to start over.')
    if state.get('signature_architecture_version') != SIGNATURE_ARCHITECTURE_VERSION:
        raise ValueError('Saved state signature architecture version does not match. Use --refresh-state to start over.')
    if state.get('api_root') != args.api_root:
        raise ValueError('Saved state api_root does not match. Use --refresh-state to start over.')
    if state.get('parameters') != expected_parameters:
        raise ValueError('Saved state parameters do not match. Use --refresh-state to start over.')


def save_state_if_enabled(args: argparse.Namespace, state: dict[str, Any]) -> None:
    """
    Saves run state unless resume has been disabled.
    Called by: lib.sampler.run_sampler_with_client()
    """
    if not args.no_resume:
        state['updated_at'] = utc_now()
        atomic_write_json(Path(args.state_file), state)


def material_parameters(args: argparse.Namespace) -> dict[str, Any]:
    """
    Returns parameters that affect resumable analysis semantics.
    Called by: new_state()
    """
    parameters = {
        'max_collections': args.max_collections,
        'max_items_per_collection': args.max_items_per_collection,
        'max_children_per_parent': args.max_children_per_parent,
        'signature_architecture_version': SIGNATURE_ARCHITECTURE_VERSION,
        'rows': args.rows,
        'include_private': args.include_private,
        'full_item_validation_sample': args.full_item_validation_sample,
        'collection_query_mode': args.collection_query_mode,
        'collection_pids': args.collection_pids,
        'skip_collections': args.skip_collections,
        'min_consistency_percent': args.min_consistency_percent,
        'fetch_all_children_max_1000': args.fetch_all_children_max_1000,
        'sample_strategy': args.sample_strategy,
        'random_seed': args.random_seed,
        'min_sample_size': args.min_sample_size,
    }
    return parameters


def ensure_checked_state(state: dict[str, Any]) -> dict[str, list[str]]:
    """
    Ensures checked state keys exist.
    Called by: load_or_initialize_state()
    """
    checked = state.setdefault('checked', {})
    checked.setdefault('collection_counts', [])
    checked.setdefault('collections', [])
    checked.setdefault('parent_items', [])
    return checked


def parent_check_key(collection_pid: str, parent_pid: str) -> str:
    """
    Builds a checked-work key for one sampled parent in one collection.
    Called by: lib.sampler.run_sampler_with_client()
    """
    key = f'{collection_pid}|{parent_pid}'
    return key


def find_saved_collection(state: dict[str, Any], pid: str) -> dict[str, Any] | None:
    """
    Finds saved collection data in state.
    Called by: lib.sampler.run_sampler_with_client()
    """
    found = None
    for collection in state.get('collections_discovered', []):
        if collection.get('pid') == pid:
            found = collection
            break
    return found


def update_saved_collection(state: dict[str, Any], collection: CollectionRef) -> None:
    """
    Updates one collection in saved state.
    Called by: lib.sampler.run_sampler_with_client()
    """
    collections = state.setdefault('collections_discovered', [])
    replaced = False
    for index, saved_collection in enumerate(collections):
        if saved_collection.get('pid') == collection.pid:
            collections[index] = collection_to_dict(collection)
            replaced = True
            break
    if not replaced:
        collections.append(collection_to_dict(collection))


def collection_to_dict(collection: CollectionRef) -> dict[str, Any]:
    """
    Converts a collection reference to JSON data.
    Called by: lib.sampler.run_sampler_with_client()
    """
    data = {'pid': collection.pid, 'name': collection.name, 'top_level_item_count': collection.top_level_item_count}
    return data
