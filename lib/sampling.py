import argparse
import random
from typing import Any

from lib.api import ApiClient
from lib.collections import count_top_level_items, solr_docs, solr_num_found
from lib.utils import evenly_spaced_offsets, first_value, natural_sort_key, normalized_rows, value_as_string


def fetch_sampled_top_level_items(client: ApiClient, collection_pid: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    """
    Fetches sampled top-level item docs for a collection.
    Called by: lib.sampler.run_sampler_with_client()
    """
    if args.sample_strategy == 'evenly-spaced':
        docs = fetch_evenly_spaced_top_level_items(client, collection_pid, args)
    elif args.sample_strategy == 'random':
        docs = fetch_random_top_level_items(client, collection_pid, args)
    else:
        docs = fetch_first_top_level_items(client, collection_pid, args)
    return docs


def fetch_first_top_level_items(client: ApiClient, collection_pid: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    """
    Fetches the first N top-level item docs for a collection.
    Called by: fetch_sampled_top_level_items()
    """
    docs: list[dict[str, Any]] = []
    start = 0
    rows = normalized_rows(args.rows)
    while len(docs) < args.max_items_per_collection:
        page = search_top_level_items(client, collection_pid, rows, start)
        page_docs = solr_docs(page)
        docs.extend(page_docs[: args.max_items_per_collection - len(docs)])
        num_found = solr_num_found(page)
        start += rows
        if not page_docs or start >= num_found:
            break
    return docs


def fetch_evenly_spaced_top_level_items(
    client: ApiClient, collection_pid: str, args: argparse.Namespace
) -> list[dict[str, Any]]:
    """
    Fetches an evenly spaced deterministic sample.
    Called by: fetch_sampled_top_level_items()
    """
    count = count_top_level_items(client, collection_pid)
    sample_count = min(args.max_items_per_collection, count)
    docs = []
    if sample_count > 0:
        starts = evenly_spaced_offsets(count, sample_count)
        for start in starts:
            page = search_top_level_items(client, collection_pid, 1, start)
            page_docs = solr_docs(page)
            if page_docs:
                docs.append(page_docs[0])
    return docs


def fetch_random_top_level_items(client: ApiClient, collection_pid: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    """
    Fetches a seeded random sample by offset.
    Called by: fetch_sampled_top_level_items()
    """
    count = count_top_level_items(client, collection_pid)
    sample_count = min(args.max_items_per_collection, count)
    docs = []
    if sample_count > 0:
        randomizer = random.Random(args.random_seed)
        starts = sorted(randomizer.sample(range(count), sample_count))
        for start in starts:
            page = search_top_level_items(client, collection_pid, 1, start)
            page_docs = solr_docs(page)
            if page_docs:
                docs.append(page_docs[0])
    return docs


def search_top_level_items(client: ApiClient, collection_pid: str, rows: int, start: int) -> dict[str, Any]:
    """
    Searches top-level items for one collection.
    Called by: fetch_first_top_level_items()
    """
    params = {
        'q': f'rel_is_member_of_collection_ssim:"{collection_pid}" AND -rel_is_part_of_ssim:* AND -object_type:bdr-collection',
        'fl': (
            'pid,primary_title,object_type,datastreams_ssi,rel_has_part_ssim,rel_is_part_of_ssim,'
            'rel_is_member_of_ssim,rel_is_derivation_of_ssim,rel_has_description_ssim,rel_has_pagination_ssim'
        ),
        'rows': rows,
        'start': start,
        'sort': 'pid asc',
    }
    data = client.search(params)
    return data


def fetch_children(client: ApiClient, parent_pid: str, args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    """
    Fetches direct children for one parent item.
    Called by: lib.sampler.run_sampler_with_client()
    """
    docs: list[dict[str, Any]] = []
    start = 0
    rows = 500
    truncated = False
    while True:
        params = {
            'q': f'rel_is_part_of_ssim:"{parent_pid}"',
            'fl': (
                'pid,primary_title,object_type,datastreams_ssi,rel_has_pagination_ssim,rel_is_derivation_of_ssim,'
                'rel_is_transcript_of_ssim,rel_is_translation_of_ssim,rel_display_label_ssi'
            ),
            'rows': rows,
            'start': start,
            'sort': 'pid asc',
        }
        data = client.search(params)
        page_docs = solr_docs(data)
        docs.extend(page_docs)
        num_found = solr_num_found(data)
        start += rows
        if start < num_found and not args.fetch_all_children:
            truncated = True
            break
        if not page_docs or start >= num_found:
            break
    sorted_docs = sorted(docs, key=child_sort_key)
    return sorted_docs, truncated


def child_sort_key(doc: dict[str, Any]) -> tuple[int, list[Any], str]:
    """
    Builds the BDR-style child sort key.
    Called by: fetch_children()
    """
    pagination = first_value(doc.get('rel_has_pagination_ssim'))
    pid = value_as_string(doc.get('pid'))
    if pagination:
        key = (0, natural_sort_key(pagination), pid)
    else:
        key = (1, [], pid)
    return key
