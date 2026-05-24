from dataclasses import dataclass, field
from typing import Any

from lib.utils import append_unique_example, first_value, value_as_string


@dataclass
class CollectionRef:
    pid: str
    name: str = ''
    top_level_item_count: int = 0


@dataclass
class ArchitectureIndex:
    dimension_candidates: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    composite_candidates: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> 'ArchitectureIndex':
        """
        Builds an index from resumable state.
        Called by: lib.sampler.run_sampler_with_client()
        """
        index = cls(
            dimension_candidates=state.get('dimension_signature_candidates', {}),
            composite_candidates=state.get('composite_architecture_candidates', {}),
        )
        return index

    @property
    def candidates(self) -> dict[str, dict[str, Any]]:
        """
        Returns composite candidates for compatibility with older callers.
        Called by: tests.test.TestMain.test_render_markdown_report_includes_architecture_and_mixed_section()
        """
        return self.composite_candidates

    def add_bundle(self, bundle: dict[str, Any], collection: CollectionRef, parent_doc: dict[str, Any]) -> None:
        """
        Adds one observed parent item signature bundle to the index.
        Called by: lib.sampler.run_sampler_with_client()
        """
        for entry in flattened_dimension_entries(bundle):
            self.add_dimension_entry(entry)
        composite = bundle['composite']
        signature_hash = composite['signature_hash']
        candidate = self.composite_candidates.setdefault(
            signature_hash,
            {
                'signature_hash': signature_hash,
                'label': composite.get('label', 'composite architecture'),
                'description': composite.get('description', ''),
                'signature': composite['signature'],
                'component_hashes': composite.get('component_hashes', {}),
                'dominant_in_collections': 0,
                'appears_in_collections': 0,
                'total_sampled_items': 0,
                'example_collections': [],
                'example_items': [],
                'observations': [],
            },
        )
        candidate['total_sampled_items'] += 1
        append_unique_example(
            candidate['example_items'],
            {
                'pid': value_as_string(parent_doc.get('pid')),
                'title': first_value(parent_doc.get('primary_title')),
                'collection_pid': collection.pid,
            },
            'pid',
            5,
        )
        append_unique_example(
            candidate['example_collections'],
            {'pid': collection.pid, 'name': collection.name},
            'pid',
            5,
        )
        append_unique_example(candidate['observations'], bundle['observation'], 'parent_pid', 5)

    def add(
        self, signature_hash: str, signature: dict[str, Any], collection: CollectionRef, parent_doc: dict[str, Any]
    ) -> None:
        """
        Adds one legacy architecture to the composite index.
        Called by: tests.test.TestMain.test_render_markdown_report_includes_architecture_and_mixed_section()
        """
        candidate = self.composite_candidates.setdefault(
            signature_hash,
            {
                'signature_hash': signature_hash,
                'label': signature.get('label', 'architecture'),
                'signature': signature,
                'dominant_in_collections': 0,
                'appears_in_collections': 0,
                'total_sampled_items': 0,
                'example_collections': [],
                'example_items': [],
            },
        )
        candidate['total_sampled_items'] += 1
        append_unique_example(
            candidate['example_items'],
            {
                'pid': value_as_string(parent_doc.get('pid')),
                'title': first_value(parent_doc.get('primary_title')),
                'collection_pid': collection.pid,
            },
            'pid',
            5,
        )
        append_unique_example(
            candidate['example_collections'],
            {'pid': collection.pid, 'name': collection.name},
            'pid',
            5,
        )

    def add_dimension_entry(self, entry: dict[str, Any]) -> None:
        """
        Adds one dimension signature entry to the index.
        Called by: ArchitectureIndex.add_bundle()
        """
        signature_type = entry['signature_type']
        signature_hash = entry['signature_hash']
        type_candidates = self.dimension_candidates.setdefault(signature_type, {})
        candidate = type_candidates.setdefault(
            signature_hash,
            {
                'signature_type': signature_type,
                'signature_hash': signature_hash,
                'label': entry.get('label', ''),
                'description': entry.get('description', ''),
                'signature': entry['signature'],
                'observed_count': 0,
                'exemplar_pids': [],
            },
        )
        candidate['observed_count'] += entry.get('observed_count', 1)
        for pid in entry.get('exemplar_pids', []):
            if pid and pid not in candidate['exemplar_pids'] and len(candidate['exemplar_pids']) < 3:
                candidate['exemplar_pids'].append(pid)

    def mark_collection_summary(self, summary: dict[str, Any]) -> None:
        """
        Records collection-level architecture presence and dominance.
        Called by: lib.sampler.run_sampler_with_client()
        """
        dominant_hash = summary.get('dominant_signature_hash')
        for signature_count in summary.get('signature_counts', []):
            signature_hash = signature_count['signature_hash']
            candidate = self.composite_candidates.get(signature_hash)
            if candidate is not None:
                candidate['appears_in_collections'] += 1
                if signature_hash == dominant_hash:
                    candidate['dominant_in_collections'] += 1


def flattened_dimension_entries(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Flattens dimension entries from one signature bundle.
    Called by: ArchitectureIndex.add_bundle()
    """
    dimensions = bundle['dimensions']
    entries = [
        dimensions['parent_relationship'],
        dimensions['parent_object_definition'],
        dimensions['children'],
        dimensions['open_access'],
        dimensions['visibility'],
        dimensions['auxiliary_relationships'],
    ]
    entries.extend(dimensions.get('child_object_definitions', []))
    return entries
