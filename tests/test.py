import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from lib.classification import classify_collection
from lib.config import (
    DEFAULT_CACHE_DIR,
    DEFAULT_MAX_CHILDREN_PER_PARENT,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SLEEP_SECONDS,
    DEFAULT_SPECIFICATIONS_DIR,
    DEFAULT_STATE_FILE,
    PROJECT_ROOT,
)
from lib.models import ArchitectureIndex, CollectionRef
from lib.report import render_markdown_report
from lib.sampling import child_sort_key, fetch_children
from lib.signatures import (
    build_item_signature,
    build_object_definition_signature,
    build_signature_bundle,
    hash_signature,
    parse_datastreams,
)
from lib.specifications import build_specification_documents, merge_signature_entry, validate_specification_document
from lib.state import load_or_initialize_state, save_state_if_enabled
from lib.utils import evenly_spaced_offsets, natural_sort_key


def load_extra_script(script_name: str) -> object:
    """
    Loads an extras script as a test module.
    Called by: TestMain.test_single_item_signature_result_builds_object_definition_entry()
    """
    path = PROJECT_ROOT / 'extras' / script_name
    spec = importlib.util.spec_from_file_location(script_name.removesuffix('.py'), path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Could not load {script_name}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_args(**overrides: object) -> argparse.Namespace:
    """
    Builds sampler args for tests.
    Called by: TestMain.test_new_state_is_saved_and_loaded()
    """
    defaults = {
        'api_root': 'https://repository.library.brown.edu/api/',
        'max_collections': 20,
        'max_items_per_collection': 100,
        'max_children_per_parent': DEFAULT_MAX_CHILDREN_PER_PARENT,
        'rows': 100,
        'sleep_seconds': DEFAULT_SLEEP_SECONDS,
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
        'fetch_all_children_max_1000': False,
        'sample_strategy': 'first',
        'random_seed': 0,
        'min_sample_size': 10,
    }
    defaults.update(overrides)
    args = argparse.Namespace(**defaults)
    return args


class FakeSearchClient:
    def __init__(self, pages: list[dict[str, object]]) -> None:
        self.pages = pages
        self.requests: list[dict[str, object]] = []

    def search(self, params: dict[str, object]) -> dict[str, object]:
        self.requests.append(params)
        page = self.pages[len(self.requests) - 1]
        return page


class FakeSingleItemClient:
    def __init__(self, doc: dict[str, object]) -> None:
        self.doc = doc
        self.requests: list[dict[str, object]] = []
        self.closed = False

    def search(self, params: dict[str, object]) -> dict[str, object]:
        self.requests.append(params)
        return {'response': {'docs': [self.doc]}}

    def close(self) -> None:
        self.closed = True


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

    def test_default_specifications_path_is_outside_project_root(self) -> None:
        """
        Checks that generated specification files live beside the project root.
        """
        default_path = Path(DEFAULT_SPECIFICATIONS_DIR)

        self.assertTrue(default_path.resolve().is_relative_to(PROJECT_ROOT.parent.resolve()))
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
        Checks that MIME types are included only for non-standard datastream tokens.
        """
        doc = {
            'datastreams_ssi': json.dumps(
                {
                    'JP2': {'mimeType': 'image/jp2'},
                    'EXTRACTED_TEXT': {'mimeType': 'text/plain'},
                    'MODS': {'mimeType': 'text/xml'},
                    'thumbnail': {'mimeType': 'image/jpeg'},
                }
            )
        }

        datastreams = parse_datastreams(doc, include_mime_types=True)

        self.assertEqual(('EXTRACTED_TEXT', 'JP2:image/jp2', 'MODS', 'thumbnail'), datastreams)

    def test_object_definition_signature_excludes_standard_datastream_mime_details(self) -> None:
        """
        Checks that standard datastream MIME types do not affect object-definition identity.
        """
        doc = {
            'object_type': 'image',
            'datastreams_ssi': json.dumps(
                {
                    'JP2': {'mimeType': 'image/jp2'},
                    'EXTRACTED_TEXT': {'mimeType': 'text/plain'},
                    'MODS': {'mimeType': 'text/xml'},
                    'thumbnail': {'mimeType': 'image/jpeg'},
                }
            ),
        }

        signature = build_object_definition_signature(doc, has_parent=False, has_children=False, is_ordered=False)

        self.assertEqual(['EXTRACTED_TEXT', 'JP2', 'MODS', 'thumbnail'], signature['datastream_ids'])
        self.assertEqual([{'id': 'JP2', 'mime_type': 'image/jp2'}], signature['datastream_details'])

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
        self.assertNotIn('children_truncated', signature)

    def test_build_signature_bundle_uses_dimension_hashes_for_composite(self) -> None:
        """
        Checks that composite signatures are built from dimension hashes.
        """
        parent_doc = {
            'pid': 'bdr:parent',
            'object_type': 'implicit-set',
            'datastreams_ssi': json.dumps({'MODS': {'mimeType': 'text/xml'}}),
        }
        child_docs = [
            {
                'pid': 'bdr:c1',
                'object_type': 'image',
                'datastreams_ssi': json.dumps({'JP2': {'mimeType': 'image/jp2'}, 'MODS': {}}),
                'rel_has_pagination_ssim': ['1'],
            }
        ]
        child_evidence = {
            'total_found': 1,
            'observed_count': 1,
            'sample_limit': 100,
            'hard_limit': 1000,
            'truncated': False,
            'fetch_all_children_max_1000': False,
            'fetch_strategy': 'first_by_pid_then_bdr_child_sort',
        }

        bundle = build_signature_bundle('bdr:collection', parent_doc, child_docs, child_evidence, 1)

        component_hashes = bundle['composite']['component_hashes']
        self.assertIn('children', component_hashes)
        self.assertEqual(
            [bundle['dimensions']['child_object_definitions'][0]['signature_hash']],
            bundle['dimensions']['children']['signature']['object_definition_hashes'],
        )
        self.assertFalse(bundle['observation']['children_truncated'])

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

    def test_fetch_children_truncates_at_sample_limit(self) -> None:
        """
        Checks that child fetching records truncation when the sample cap is hit.
        """
        args = build_args(max_children_per_parent=2)
        client = FakeSearchClient(
            [
                {
                    'response': {
                        'numFound': 3,
                        'docs': [{'pid': 'bdr:2'}, {'pid': 'bdr:1'}],
                    }
                }
            ]
        )

        result = fetch_children(client, 'bdr:parent', args)

        self.assertEqual(2, result.observed_count)
        self.assertEqual(3, result.total_found)
        self.assertTrue(result.truncated)
        self.assertEqual(2, client.requests[0]['rows'])

    def test_fetch_children_max_1000_paginates_until_complete(self) -> None:
        """
        Checks that max-1000 child fetching paginates until all observed children are fetched.
        """
        args = build_args(fetch_all_children_max_1000=True)
        client = FakeSearchClient(
            [
                {'response': {'numFound': 501, 'docs': [{'pid': f'bdr:{index}'} for index in range(500)]}},
                {'response': {'numFound': 501, 'docs': [{'pid': 'bdr:501'}]}},
            ]
        )

        result = fetch_children(client, 'bdr:parent', args)

        self.assertEqual(501, result.observed_count)
        self.assertFalse(result.truncated)
        self.assertEqual([500, 500], [request['rows'] for request in client.requests])

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
            state['composite_architecture_candidates']['abc123'] = {'signature_hash': 'abc123'}
            save_state_if_enabled(args, state)

            loaded = load_or_initialize_state(args)

        self.assertEqual(['bdr:collection'], loaded['checked']['collections'])
        self.assertEqual({'signature_hash': 'abc123'}, loaded['composite_architecture_candidates']['abc123'])

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
            'composite_architectures': list(index.candidates.values()),
        }

        markdown = render_markdown_report(result)

        self.assertIn('implicit-set with image children', markdown)
        self.assertIn('Collections With Mixed Architectures', markdown)
        self.assertIn('`bdr:collection`', markdown)

    def test_specification_documents_have_expected_structure(self) -> None:
        """
        Checks that specification documents are structurally valid.
        """
        result = {
            'api_root': 'https://repository.library.brown.edu/api/',
            'dimension_signatures': {
                'visibility': {
                    'abc123': {
                        'signature_hash': 'abc123',
                        'label': 'public api observed',
                        'description': 'Observed through public API.',
                        'exemplar_pids': ['bdr:1'],
                        'signature': {'visibility_scope': 'public_api_observed'},
                    }
                }
            },
            'composite_architectures': [],
        }

        documents = build_specification_documents(result)

        validate_specification_document(documents['visibility'])
        entry = documents['visibility']['signatures']['public_api_observed_abc123']
        self.assertIn('public_api_observed', entry['signature'].values())
        self.assertNotIn('observed_count', entry)

    def test_merge_signature_entry_preserves_label_like_fields(self) -> None:
        """
        Checks that YAML merge behavior preserves human review labels.
        """
        existing = {
            'signature_hash': 'abc123',
            'label': 'Reviewed label',
            'description': 'Reviewed description',
            'exemplar_pids': ['bdr:old'],
            'signature': {'a': 1},
        }
        new = {
            'signature_hash': 'abc123',
            'label': 'Generated label',
            'description': 'Generated description',
            'exemplar_pids': ['bdr:new'],
            'signature': {'a': 1},
        }

        merged = merge_signature_entry(existing, new)

        self.assertEqual('Reviewed label', merged['label'])
        self.assertEqual('Reviewed description', merged['description'])
        self.assertEqual(['bdr:old', 'bdr:new'], merged['exemplar_pids'])

    def test_single_item_signature_result_builds_object_definition_entry(self) -> None:
        """
        Checks that the single-item helper builds an object-definition signature.
        """
        module = load_extra_script('get_object_definition_signature.py')
        fake_client = FakeSingleItemClient(
            {
                'pid': 'bdr:item',
                'primary_title': 'Example Item',
                'object_type': 'pdf',
                'mods_type_of_resource': 'text',
                'datastreams_ssi': json.dumps(
                    {
                        'EXTRACTED_TEXT': {'mimeType': 'text/plain'},
                        'PDF': {'mimeType': 'application/pdf'},
                    }
                ),
                'rel_is_part_of_ssim': ['bdr:parent'],
                'rel_has_part_ssim': [],
            }
        )
        args = argparse.Namespace(
            api_root='https://repository.library.brown.edu/api/',
            pid='bdr:item',
            specifications_dir=DEFAULT_SPECIFICATIONS_DIR,
            compare_specifications=False,
        )
        module.build_client = lambda _args: fake_client

        result = module.build_result(args)

        self.assertTrue(fake_client.closed)
        self.assertEqual(['api_root', 'pid', 'title', 'signature_entry'], list(result))
        self.assertEqual('bdr:item', result['pid'])
        self.assertEqual('object_definition', result['signature_entry']['signature_type'])
        self.assertNotIn('observed_count', result['signature_entry'])
        formatted_result = module.format_result_json(result)
        self.assertLess(formatted_result.find('"title"'), formatted_result.find('"signature_entry"'))
        self.assertEqual(['EXTRACTED_TEXT', 'PDF'], result['signature_entry']['signature']['datastream_ids'])
        self.assertEqual(
            [{'id': 'PDF', 'mime_type': 'application/pdf'}],
            result['signature_entry']['signature']['datastream_details'],
        )

    def test_single_item_signature_finds_specification_match(self) -> None:
        """
        Checks that the single-item helper can compare against object-definition specifications.
        """
        module = load_extra_script('get_object_definition_signature.py')
        with tempfile.TemporaryDirectory() as temp_dir:
            spec_dir = Path(temp_dir)
            spec_path = spec_dir / 'object_definition_signatures.yaml'
            spec_path.write_text(
                '\n'.join(
                    [
                        'signatures:',
                        '  pdf_object_definition_abc123:',
                        '    signature_hash: abc123',
                        '    label: pdf object definition',
                        '    description: Reviewed PDF signature.',
                    ]
                ),
                encoding='utf-8',
            )

            match = module.find_specification_match(spec_dir, 'abc123')

        self.assertTrue(match['matched'])
        self.assertNotIn('path', match)
        self.assertFalse(Path(match['relative_path']).is_absolute())
        self.assertTrue(match['relative_path'].endswith('object_definition_signatures.yaml'))
        self.assertEqual('pdf_object_definition_abc123', match['entry_key'])

    def test_single_item_signature_handles_missing_specification_file(self) -> None:
        """
        Checks that missing specification comparison files are reported clearly.
        """
        module = load_extra_script('get_object_definition_signature.py')
        with tempfile.TemporaryDirectory() as temp_dir:
            spec_dir = Path(temp_dir)

            match = module.find_specification_match(spec_dir, 'abc123')

        self.assertFalse(match['matched'])
        self.assertNotIn('path', match)
        self.assertIn('Comparison file could not be found at', match['message'])
        self.assertFalse(Path(match['relative_path']).is_absolute())
        self.assertTrue(match['relative_path'].endswith('object_definition_signatures.yaml'))


if __name__ == '__main__':
    unittest.main()
