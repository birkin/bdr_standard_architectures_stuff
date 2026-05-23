import argparse
import json
import tempfile
import unittest
from pathlib import Path

from lib.classification import classify_collection
from lib.config import (
    DEFAULT_CACHE_DIR,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_STATE_FILE,
    PROJECT_ROOT,
)
from lib.models import ArchitectureIndex, CollectionRef
from lib.report import render_markdown_report
from lib.sampling import child_sort_key
from lib.signatures import build_item_signature, hash_signature, parse_datastreams
from lib.state import load_or_initialize_state, save_state_if_enabled
from lib.utils import evenly_spaced_offsets, natural_sort_key


def build_args(**overrides: object) -> argparse.Namespace:
    """
    Builds sampler args for tests.
    Called by: TestMain.test_new_state_is_saved_and_loaded()
    """
    defaults = {
        'api_root': 'https://repository.library.brown.edu/api/',
        'max_collections': 20,
        'max_items_per_collection': 100,
        'rows': 100,
        'sleep_seconds': 0.5,
        'output_json': DEFAULT_OUTPUT_JSON,
        'output_md': DEFAULT_OUTPUT_MD,
        'cache_dir': DEFAULT_CACHE_DIR,
        'state_file': DEFAULT_STATE_FILE,
        'refresh_cache': False,
        'refresh_state': False,
        'no_resume': False,
        'include_private': False,
        'full_item_validation_sample': 0,
        'collection_query_mode': 'public-top-level',
        'collection_pids': '',
        'skip_collections': '',
        'min_consistency_percent': 90.0,
        'top_architectures': 25,
        'include_singletons': False,
        'include_mime_types': False,
        'fetch_all_children': False,
        'sample_strategy': 'first',
        'random_seed': 0,
        'min_sample_size': 10,
    }
    defaults.update(overrides)
    args = argparse.Namespace(**defaults)
    return args


class TestMain(unittest.TestCase):
    def test_default_output_paths_are_outside_project_root(self) -> None:
        """
        Checks that generated default paths live in the sibling output directory.
        """
        default_paths = [
            Path(DEFAULT_OUTPUT_JSON),
            Path(DEFAULT_OUTPUT_MD),
            Path(DEFAULT_CACHE_DIR),
            Path(DEFAULT_STATE_FILE),
        ]

        for default_path in default_paths:
            self.assertTrue(default_path.resolve().is_relative_to(DEFAULT_OUTPUT_ROOT.resolve()))
            self.assertFalse(default_path.resolve().is_relative_to(PROJECT_ROOT.resolve()))

    def test_parse_datastreams_returns_sorted_ids(self) -> None:
        """
        Checks that datastream JSON is normalized to sorted IDs.
        """
        doc = {'datastreams_ssi': json.dumps({'thumbnail': {}, 'MODS': {}, 'JP2': {'mimeType': 'image/jp2'}})}

        datastreams = parse_datastreams(doc)

        self.assertEqual(('JP2', 'MODS', 'thumbnail'), datastreams)

    def test_parse_datastreams_can_include_mime_type(self) -> None:
        """
        Checks that MIME types can be included in datastream tokens.
        """
        doc = {'datastreams_ssi': json.dumps({'JP2': {'mimeType': 'image/jp2'}, 'MODS': {}})}

        datastreams = parse_datastreams(doc, include_mime_types=True)

        self.assertEqual(('JP2:image/jp2', 'MODS'), datastreams)

    def test_parse_datastreams_handles_invalid_json(self) -> None:
        """
        Checks that invalid datastream JSON receives a sentinel token.
        """
        doc = {'datastreams_ssi': '{bad json'}

        datastreams = parse_datastreams(doc)

        self.assertEqual(('__INVALID_DATASTREAMS_JSON__',), datastreams)

    def test_build_item_signature_groups_children(self) -> None:
        """
        Checks that child signatures are grouped by object type and datastreams.
        """
        args = build_args()
        parent_doc = {'pid': 'bdr:parent', 'object_type': 'implicit-set', 'datastreams_ssi': json.dumps({'MODS': {}})}
        child_docs = [
            {'pid': 'bdr:c1', 'object_type': 'image', 'datastreams_ssi': json.dumps({'JP2': {}, 'MODS': {}})},
            {'pid': 'bdr:c2', 'object_type': 'image', 'datastreams_ssi': json.dumps({'MODS': {}, 'JP2': {}})},
            {'pid': 'bdr:c3', 'object_type': 'pdf', 'datastreams_ssi': json.dumps({'PDF': {}})},
        ]

        signature = build_item_signature(parent_doc, child_docs, args)

        self.assertEqual('implicit-set', signature['object_type'])
        self.assertEqual('few:2-9', signature['child_count_bucket'])
        self.assertEqual(2, len(signature['child_groups']))
        self.assertEqual('few:2-9', signature['child_groups'][0]['count_bucket'])

    def test_hash_signature_is_stable_for_key_order(self) -> None:
        """
        Checks that signature hashing is independent of dictionary key order.
        """
        first = {'object_type': 'image', 'datastreams': ['JP2', 'MODS']}
        second = {'datastreams': ['JP2', 'MODS'], 'object_type': 'image'}

        first_hash = hash_signature(first)
        second_hash = hash_signature(second)

        self.assertEqual(first_hash, second_hash)

    def test_child_sort_key_uses_natural_pagination_then_pid(self) -> None:
        """
        Checks that paginated children sort naturally before unordered children.
        """
        docs = [
            {'pid': 'bdr:3'},
            {'pid': 'bdr:2', 'rel_has_pagination_ssim': ['10']},
            {'pid': 'bdr:1', 'rel_has_pagination_ssim': ['2']},
        ]

        sorted_docs = sorted(docs, key=child_sort_key)

        self.assertEqual(['bdr:1', 'bdr:2', 'bdr:3'], [doc['pid'] for doc in sorted_docs])
        self.assertEqual(['page', 12], natural_sort_key('page12'))

    def test_classify_collection_marks_mostly_uniform(self) -> None:
        """
        Checks that dominant signature percentage drives collection classification.
        """
        args = build_args(min_sample_size=5, min_consistency_percent=80.0)
        collection = CollectionRef(pid='bdr:collection', name='Collection', top_level_item_count=5)

        summary = classify_collection(collection, ['a', 'a', 'a', 'a', 'b'], args)

        self.assertEqual('mostly_uniform', summary['classification'])
        self.assertEqual('a', summary['dominant_signature_hash'])
        self.assertEqual(0.8, summary['dominant_signature_percent'])

    def test_evenly_spaced_offsets_include_edges(self) -> None:
        """
        Checks that deterministic sample offsets include first and last records.
        """
        offsets = evenly_spaced_offsets(10, 4)

        self.assertEqual([0, 3, 6, 9], offsets)

    def test_new_state_is_saved_and_loaded(self) -> None:
        """
        Checks that resumable state persists checked work and candidates.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / 'state.json'
            args = build_args(state_file=str(state_file))
            state = load_or_initialize_state(args)
            state['checked']['collections'].append('bdr:collection')
            state['common_architecture_candidates']['abc123'] = {'signature_hash': 'abc123'}
            save_state_if_enabled(args, state)

            loaded = load_or_initialize_state(args)

        self.assertEqual(['bdr:collection'], loaded['checked']['collections'])
        self.assertEqual({'signature_hash': 'abc123'}, loaded['common_architecture_candidates']['abc123'])

    def test_state_parameter_mismatch_raises(self) -> None:
        """
        Checks that incompatible state does not resume silently.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / 'state.json'
            args = build_args(state_file=str(state_file))
            state = load_or_initialize_state(args)
            save_state_if_enabled(args, state)
            changed_args = build_args(state_file=str(state_file), rows=50)

            with self.assertRaises(ValueError):
                load_or_initialize_state(changed_args)

    def test_render_markdown_report_includes_architecture_and_mixed_section(self) -> None:
        """
        Checks that Markdown rendering includes summary architecture details.
        """
        index = ArchitectureIndex()
        signature = {
            'object_type': 'implicit-set',
            'datastreams': ['MODS'],
            'child_groups': [{'object_type': 'image', 'datastreams': ['JP2'], 'count_bucket': 'many:10+'}],
        }
        index.candidates['abc123'] = {
            'signature_hash': 'abc123',
            'label': 'implicit-set with image children',
            'signature': signature,
            'dominant_in_collections': 1,
            'appears_in_collections': 1,
            'total_sampled_items': 10,
            'example_collections': [{'pid': 'bdr:collection', 'name': 'Collection'}],
            'example_items': [{'pid': 'bdr:item', 'title': 'Item'}],
        }
        result = {
            'generated_at': '2026-05-22T00:00:00+00:00',
            'collections_considered': [
                {
                    'pid': 'bdr:collection',
                    'name': 'Collection',
                    'sampled_item_count': 10,
                    'classification': 'mixed',
                    'dominant_signature_percent': 0.7,
                }
            ],
            'architectures': list(index.candidates.values()),
        }

        markdown = render_markdown_report(result)

        self.assertIn('implicit-set with image children', markdown)
        self.assertIn('Collections With Mixed Architectures', markdown)
        self.assertIn('`bdr:collection`', markdown)


if __name__ == '__main__':
    unittest.main()
