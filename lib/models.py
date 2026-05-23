from dataclasses import dataclass, field
from typing import Any

from lib.signatures import label_signature
from lib.utils import append_unique_example, first_value, value_as_string


@dataclass
class CollectionRef:
    pid: str
    name: str = ''
    top_level_item_count: int = 0


@dataclass
class ArchitectureIndex:
    candidates: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> 'ArchitectureIndex':
        """
        Builds an index from resumable state.
        Called by: lib.sampler.run_sampler_with_client()
        """
        index = cls(candidates=state.get('common_architecture_candidates', {}))
        return index

    def add(
        self, signature_hash: str, signature: dict[str, Any], collection: CollectionRef, parent_doc: dict[str, Any]
    ) -> None:
        """
        Adds one observed parent item architecture to the index.
        Called by: lib.sampler.run_sampler_with_client()
        """
        candidate = self.candidates.setdefault(
            signature_hash,
            {
                'signature_hash': signature_hash,
                'label': label_signature(signature),
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

    def mark_collection_summary(self, summary: dict[str, Any]) -> None:
        """
        Records collection-level architecture presence and dominance.
        Called by: lib.sampler.run_sampler_with_client()
        """
        dominant_hash = summary.get('dominant_signature_hash')
        for signature_count in summary.get('signature_counts', []):
            signature_hash = signature_count['signature_hash']
            candidate = self.candidates.get(signature_hash)
            if candidate is not None:
                candidate['appears_in_collections'] += 1
                if signature_hash == dominant_hash:
                    candidate['dominant_in_collections'] += 1
