import datetime
import json
import re
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """
    Writes JSON atomically.
    Called by: lib.state.save_state_if_enabled()
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as file_object:
        json.dump(data, file_object, indent=2, sort_keys=True)
        file_object.write('\n')
        temp_path = Path(file_object.name)
    temp_path.replace(path)


def write_json(path: Path, data: dict[str, Any]) -> None:
    """
    Writes final JSON output.
    Called by: main.main()
    """
    atomic_write_json(path, data)


def write_markdown(path: Path, markdown: str) -> None:
    """
    Writes final Markdown output.
    Called by: main.main()
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as file_object:
        file_object.write(markdown)
        temp_path = Path(file_object.name)
    temp_path.replace(path)


def utc_now() -> str:
    """
    Returns the current UTC time in ISO format.
    Called by: lib.state.new_state()
    """
    value = datetime.datetime.now(datetime.UTC).isoformat()
    return value


def first_value(value: Any) -> str:
    """
    Converts scalar or list values to a first string.
    Called by: lib.collections.extract_title()
    """
    if isinstance(value, list):
        output = value_as_string(value[0]) if value else ''
    else:
        output = value_as_string(value)
    return output


def value_as_string(value: Any) -> str:
    """
    Converts a value to a string safely.
    Called by: first_value()
    """
    output = '' if value is None else str(value)
    return output


def parse_csv(value: str) -> list[str]:
    """
    Parses a comma-separated option value.
    Called by: lib.collections.discover_collections()
    """
    values = [part.strip() for part in value.split(',') if part.strip()]
    return values


def natural_sort_key(value: str) -> list[Any]:
    """
    Splits a string into natural-sort parts.
    Called by: lib.sampling.child_sort_key()
    """
    parts: list[Any] = []
    for part in re.split(r'(\d+)', value):
        if not part:
            continue
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(part.lower())
    return parts


def evenly_spaced_offsets(total_count: int, sample_count: int) -> list[int]:
    """
    Builds deterministic evenly spaced offsets.
    Called by: lib.sampling.fetch_evenly_spaced_top_level_items()
    """
    if sample_count <= 1:
        offsets = [0] if total_count else []
    else:
        max_offset = total_count - 1
        offsets = [round(index * max_offset / (sample_count - 1)) for index in range(sample_count)]
    return offsets


def format_inline_code_list(values: list[str]) -> str:
    """
    Formats a list for Markdown display.
    Called by: lib.report.render_architecture_section()
    """
    if values:
        text = ', '.join(f'`{value}`' for value in values)
    else:
        text = 'none'
    return text


def count_classification(collections: list[dict[str, Any]], classification: str) -> int:
    """
    Counts collections by classification.
    Called by: lib.report.render_markdown_report()
    """
    count = sum(1 for collection in collections if collection.get('classification') == classification)
    return count


def normalized_rows(rows: int) -> int:
    """
    Keeps row requests inside public Search API limits.
    Called by: lib.sampling.fetch_first_top_level_items()
    """
    normalized = max(1, min(rows, 500))
    return normalized


def append_unique_example(items: list[dict[str, Any]], item: dict[str, Any], key: str, limit: int) -> None:
    """
    Appends a bounded unique example item.
    Called by: lib.models.ArchitectureIndex.add()
    """
    existing = {existing_item.get(key) for existing_item in items}
    if item.get(key) not in existing and len(items) < limit:
        items.append(item)
