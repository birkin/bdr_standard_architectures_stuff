import argparse
from typing import Any

from lib.models import ArchitectureIndex, CollectionRef
from lib.config import SIGNATURE_ARCHITECTURE_VERSION
from lib.state import material_parameters
from lib.utils import count_classification, format_inline_code_list, utc_now


def build_result(
    args: argparse.Namespace,
    collection_summaries: list[dict[str, Any]],
    architecture_index: ArchitectureIndex,
    collection_by_pid: dict[str, CollectionRef],
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Builds final JSON report data.
    Called by: lib.sampler.run_sampler_with_client()
    """
    all_composite_architectures = sorted(
        architecture_index.composite_candidates.values(),
        key=lambda item: (
            item.get('dominant_in_collections', 0),
            item.get('total_sampled_items', 0),
            item.get('appears_in_collections', 0),
        ),
        reverse=True,
    )
    composite_architectures = list(all_composite_architectures)
    if not args.include_singletons:
        composite_architectures = [item for item in composite_architectures if item.get('total_sampled_items', 0) > 1]
    composite_architectures = composite_architectures[: args.top_architectures]
    result = {
        'generated_at': utc_now(),
        'api_root': args.api_root,
        'scope': 'public/discoverable unless run against an authenticated or internal API root',
        'signature_architecture_version': SIGNATURE_ARCHITECTURE_VERSION,
        'parameters': material_parameters(args),
        'collections_considered': collection_summaries,
        'composite_architectures': composite_architectures,
        'specification_composite_architectures': all_composite_architectures,
        'dimension_signatures': architecture_index.dimension_candidates,
        'child_sampling': build_child_sampling_summary(state),
        'warnings': state.get('warnings', []),
        'collection_count': len(collection_by_pid),
    }
    return result


def render_markdown_report(result: dict[str, Any]) -> str:
    """
    Renders a human-readable Markdown report.
    Called by: main.main()
    """
    collections = result['collections_considered']
    architectures = result.get('composite_architectures', result.get('architectures', []))
    lines = [
        '# Common BDR Object Architectures',
        '',
        f'Generated: {result["generated_at"]}',
        '',
        '## Summary',
        '',
        f'- Collections scanned: {len(collections)}',
        f'- Top-level items sampled: {sum(collection.get("sampled_item_count", 0) for collection in collections)}',
        f'- Unique composite architectures reported: {len(architectures)}',
        f'- Parent observations with truncated children: {result.get("child_sampling", {}).get("truncated_parent_observations", 0)}',
        f'- Uniform collections: {count_classification(collections, "uniform")}',
        f'- Mostly uniform collections: {count_classification(collections, "mostly_uniform")}',
        f'- Mixed collections: {count_classification(collections, "mixed")}',
        '',
        '## Most Common Composite Architectures',
        '',
    ]
    if not architectures:
        lines.extend(['No architectures matched the reporting filters.', ''])
    for index, architecture in enumerate(architectures, 1):
        lines.extend(render_architecture_section(index, architecture))
    lines.extend(render_mixed_collections(collections))
    markdown = '\n'.join(lines).rstrip() + '\n'
    return markdown


def render_architecture_section(index: int, architecture: dict[str, Any]) -> list[str]:
    """
    Renders one architecture section.
    Called by: render_markdown_report()
    """
    signature = architecture['signature']
    component_hashes = architecture.get('component_hashes', signature.get('component_hashes', {}))
    lines = [
        f'### {index}. {architecture.get("label", "architecture")}',
        '',
        f'- Signature: `{architecture["signature_hash"]}`',
        f'- Dominant in collections: {architecture.get("dominant_in_collections", 0)}',
        f'- Appears in collections: {architecture.get("appears_in_collections", 0)}',
        f'- Sampled items: {architecture.get("total_sampled_items", 0)}',
        '- Components:',
    ]
    if component_hashes:
        for component_type, signature_hash in component_hashes.items():
            lines.append(f'  - {component_type}: `{signature_hash}`')
    else:
        lines.append(f'- Parent object_type: `{signature.get("object_type", "unknown")}`')
        lines.append(f'- Parent datastreams: {format_inline_code_list(signature.get("datastreams", []))}')
    lines.extend(['- Example collections:'])
    for collection in architecture.get('example_collections', []):
        lines.append(f'  - `{collection["pid"]}` {collection.get("name", "")}'.rstrip())
    lines.extend(['- Example items:'])
    for item in architecture.get('example_items', []):
        lines.append(f'  - `{item["pid"]}` {item.get("title", "")}'.rstrip())
    lines.append('')
    return lines


def build_child_sampling_summary(state: dict[str, Any]) -> dict[str, Any]:
    """
    Builds a summary of child sampling evidence.
    Called by: build_result()
    """
    parent_results = state.get('parent_item_signature_results', {})
    observations = [result.get('observation', {}) for result in parent_results.values()]
    truncated = sum(1 for observation in observations if observation.get('children_truncated'))
    sample_limits = sorted({observation.get('child_sample_limit') for observation in observations if observation})
    fetch_strategies = sorted({observation.get('child_fetch_strategy') for observation in observations if observation})
    summary = {
        'parent_observation_count': len(observations),
        'truncated_parent_observations': truncated,
        'sample_limits': sample_limits,
        'fetch_strategies': fetch_strategies,
    }
    return summary


def render_mixed_collections(collections: list[dict[str, Any]]) -> list[str]:
    """
    Renders mixed collection report sections.
    Called by: render_markdown_report()
    """
    lines = ['', '## Collections With Mixed Architectures', '']
    mixed = [collection for collection in collections if collection.get('classification') == 'mixed']
    if not mixed:
        lines.append('No mixed collections found in the sampled data.')
    for collection in mixed:
        percent = collection.get('dominant_signature_percent', 0) * 100
        lines.append(
            f'- `{collection["pid"]}` {collection.get("name", "")}: '
            f'{percent:.1f}% dominant signature over {collection.get("sampled_item_count", 0)} sampled items'
        )
    return lines
