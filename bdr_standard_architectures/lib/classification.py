import argparse
from typing import Any

from lib.models import CollectionRef


def classify_collection(collection: CollectionRef, signature_hashes: list[str], args: argparse.Namespace) -> dict[str, Any]:
    """
    Classifies one collection by signature consistency.
    Called by: lib.sampler.run_sampler_with_client()
    """
    signature_counts = count_values(signature_hashes)
    sampled_count = len(signature_hashes)
    dominant_signature_hash = ''
    dominant_count = 0
    if signature_counts:
        dominant = signature_counts[0]
        dominant_signature_hash = dominant['signature_hash']
        dominant_count = dominant['count']
    dominant_percent = dominant_count / sampled_count if sampled_count else 0
    classification = classify_consistency(sampled_count, dominant_percent, args)
    summary = {
        'pid': collection.pid,
        'name': collection.name,
        'top_level_item_count': collection.top_level_item_count,
        'sampled_item_count': sampled_count,
        'dominant_signature_hash': dominant_signature_hash,
        'dominant_signature_percent': dominant_percent,
        'classification': classification,
        'signature_counts': signature_counts,
        'warnings': [],
    }
    return summary


def classify_consistency(sampled_count: int, dominant_percent: float, args: argparse.Namespace) -> str:
    """
    Converts consistency metrics to a classification label.
    Called by: classify_collection()
    """
    if sampled_count < args.min_sample_size:
        classification = 'insufficient_sample'
    elif dominant_percent == 1:
        classification = 'uniform'
    elif dominant_percent >= args.min_consistency_percent / 100:
        classification = 'mostly_uniform'
    else:
        classification = 'mixed'
    return classification


def count_values(values: list[str]) -> list[dict[str, Any]]:
    """
    Counts strings for report output.
    Called by: classify_collection()
    """
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    output = [{'signature_hash': key, 'count': value} for key, value in counts.items()]
    output.sort(key=lambda item: item['count'], reverse=True)
    return output
