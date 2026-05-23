import argparse
from typing import Any

from lib.models import ArchitectureIndex, CollectionRef
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
    architectures = sorted(
        architecture_index.candidates.values(),
        key=lambda item: (
            item.get('dominant_in_collections', 0),
            item.get('total_sampled_items', 0),
            item.get('appears_in_collections', 0),
        ),
        reverse=True,
    )
    if not args.include_singletons:
        architectures = [item for item in architectures if item.get('total_sampled_items', 0) > 1]
    architectures = architectures[: args.top_architectures]
    result = {
        'generated_at': utc_now(),
        'api_root': args.api_root,
        'scope': 'public/discoverable unless run against an authenticated or internal API root',
        'parameters': material_parameters(args),
        'collections_considered': collection_summaries,
        'architectures': architectures,
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
    architectures = result['architectures']
    lines = [
        '# Common BDR Object Architectures',
        '',
        f'Generated: {result["generated_at"]}',
        '',
        '## Summary',
        '',
        f'- Collections scanned: {len(collections)}',
        f'- Top-level items sampled: {sum(collection.get("sampled_item_count", 0) for collection in collections)}',
        f'- Unique architectures reported: {len(architectures)}',
        f'- Uniform collections: {count_classification(collections, "uniform")}',
        f'- Mostly uniform collections: {count_classification(collections, "mostly_uniform")}',
        f'- Mixed collections: {count_classification(collections, "mixed")}',
        '',
        '## Most Common Architectures',
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
    lines = [
        f'### {index}. {architecture.get("label", "architecture")}',
        '',
        f'- Signature: `{architecture["signature_hash"]}`',
        f'- Dominant in collections: {architecture.get("dominant_in_collections", 0)}',
        f'- Appears in collections: {architecture.get("appears_in_collections", 0)}',
        f'- Sampled items: {architecture.get("total_sampled_items", 0)}',
        f'- Parent object_type: `{signature.get("object_type", "unknown")}`',
        f'- Parent datastreams: {format_inline_code_list(signature.get("datastreams", []))}',
        '- Children:',
    ]
    child_groups = signature.get('child_groups', [])
    if child_groups:
        for child_group in child_groups:
            lines.append(
                '  - '
                f'{child_group["count_bucket"]} `{child_group["object_type"]}` children '
                f'with {format_inline_code_list(child_group.get("datastreams", []))}'
            )
    else:
        lines.append('  - none')
    lines.extend(['- Example collections:'])
    for collection in architecture.get('example_collections', []):
        lines.append(f'  - `{collection["pid"]}` {collection.get("name", "")}'.rstrip())
    lines.extend(['- Example items:'])
    for item in architecture.get('example_items', []):
        lines.append(f'  - `{item["pid"]}` {item.get("title", "")}'.rstrip())
    lines.append('')
    return lines


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
