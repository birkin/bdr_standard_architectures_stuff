# Plan: implement specific signature architecture

## Table Of Contents

- [Purpose](#purpose)
- [Key Behavioral Changes](#key-behavioral-changes)
- [Current Implementation Context](#current-implementation-context)
- [Coding Directives To Preserve](#coding-directives-to-preserve)
- [Target Signature Model](#target-signature-model)
- [Child Object Sampling Strategy](#child-object-sampling-strategy)
- [API Fields To Use And Possibly Expand](#api-fields-to-use-and-possibly-expand)
- [Proposed Module Changes](#proposed-module-changes)
- [Specification File Semantics](#specification-file-semantics)
- [Output And CLI Design](#output-and-cli-design)
- [State And Cache Compatibility](#state-and-cache-compatibility)
- [Testing Plan](#testing-plan)
- [Implementation Sequence](#implementation-sequence)
- [Suggested Smoke Commands After Implementation](#suggested-smoke-commands-after-implementation)
- [Risks And Mitigations](#risks-and-mitigations)
- [Open Decisions For Implementation Session](#open-decisions-for-implementation-session)
- [Questions / Decision Points For Birkin](#questions--decision-points-for-birkin)
- [Recommended Initial Assumptions](#recommended-initial-assumptions)

## Purpose

Update the current BDR architecture sampler so it captures smaller, named, machine-and-human-readable signature dimensions and composes them into composite architecture signatures.

The implementation should preserve as much of the current working behavior as reasonably possible:

- CLI-driven scans.
- Public BDR API defaults.
- API response caching.
- Resumable run state.
- Multiple scan/sampling/report flags.
- JSON and Markdown reports.
- Default selection of 20 collections.
- Default sampling of 100 top-level parent items per collection.

The main change is that the current single coarse parent/children architecture signature should become an output of several dimension signatures, with enough evidence saved to build YAML specification files and human-reviewable reports.

Example new files:

```
specifications/parent_relationship_signatures.yaml
specifications/object_definition_signatures.yaml
specifications/open_access_signatures.yaml
specifications/visibility_signatures.yaml
specifications/auxiliary_relationships_signatures.yaml
specifications/children_signatures.yaml
specifications/composite_architecture_signatures.yaml
```

Important implementation correction: the current coarse signature includes `children_truncated` inside the hashed signature. In the new architecture, child truncation/sampling status should move to observation/evidence metadata and should not participate in dimension or composite identity.

## Key Behavioral Changes

- Default API pacing should change from `--sleep-seconds 0.5` to `--sleep-seconds 2.0` because the new work may inspect more child objects and therefore create more server load.
- Keep the current default of `--max-items-per-collection 100`; this remains the default parent-item sample size per selected collection.
- Add a new child-object sample cap, tentatively named `--max-children-per-parent`, defaulting to `100`.
- Keep `--fetch-all-children`, but reinterpret it carefully:
  - without `--fetch-all-children`, fetch at most `--max-children-per-parent` children per sampled parent and mark child evidence as truncated or sampled when more children exist;
  - with `--fetch-all-children`, fetch all direct children up to a hard safety cap of 1,000 children per parent.
- Do not include child truncation/sample metadata in signature hashes. Include it in observation metadata, state, JSON output, and Markdown warnings/notes.
- Keep API response caching in `lib.cache.Cache` and `lib.api.ApiClient` unchanged unless a cache-key version bump is needed for materially different request parameters.
- Keep the existing sampler workflow and state checkpointing, but change the data stored for each parent from one `signature_hash` to a richer observation/signature result.

## Current Implementation Context

The current code is organized around a straightforward pipeline:

1. `main.py` parses CLI flags and writes JSON/Markdown outputs.
2. `lib.sampler.run_sampler()` creates `Cache`, `ApiClient`, and resumable state.
3. `lib.collections` discovers and counts collections.
4. `lib.sampling.fetch_sampled_top_level_items()` fetches up to `--max-items-per-collection` top-level parent records per collection.
5. `lib.sampling.fetch_children()` fetches direct children for each sampled parent.
6. `lib.signatures.build_item_signature()` builds one coarse signature from parent object type, parent datastreams, child count bucket, truncation status, and grouped child records.
7. `lib.signatures.hash_signature()` deterministically hashes the signature JSON to a 12-character hash.
8. `lib.models.ArchitectureIndex` accumulates architecture candidates and examples.
9. `lib.classification.classify_collection()` classifies a collection based on dominant parent-item signatures.
10. `lib.report` builds the JSON result and Markdown report.

The existing API cache is valuable and should be preserved. `ApiClient._request_json()` keys cache entries by script version, API root, path, and request params. Because new child queries will include a different `rows` value or possibly additional fields, those requests naturally receive distinct cache files.

The existing resumable state is also valuable. It currently tracks checked collection counts, checked collections, checked parent items, parent item signature hashes, architecture candidates, collection summaries, and warnings. The implementation should retain this checkpointing pattern, but it will likely need a state schema/version update because the meaning and shape of stored signatures will change.

Current tests live in one file, `tests/test.py`, with a shared `build_args()` helper. Implementation should update that helper immediately after adding CLI/default args so older tests fail for behavior changes rather than missing attributes.

## Coding Directives To Preserve

Follow `AGENTS.md` as the source of truth:

- Use Python 3.12 style type hints.
- Prefer builtin generics and PEP 604 unions.
- Keep `main()` simple.
- Put substantive logic in `lib/` modules.
- Use `httpx` for HTTP.
- Use standard-library `unittest` for tests.
- Match existing docstring style, including `Called by: ...` as the last line of non-test function docstrings.
- Inspect `ruff.toml`: line length is 125, quote style is single quotes.
- Run tests with `uv run ./run_tests.py` when implementation is complete.

## Target Signature Model

Implement signatures in three layers:

### 1. Observation

An observation is the raw normalized evidence for one sampled parent item and its sampled children.

It should include scan/evidence metadata that helps evaluate confidence but usually should not define architecture identity:

- collection PID and parent PID for traceability;
- number of parent items sampled for the collection;
- number of children observed for the parent;
- total child count reported by the API if known;
- whether child evidence was capped by `--max-children-per-parent`;
- whether child evidence was capped only because `--fetch-all-children` was not set;
- public API visibility scope;
- fields used for detection.

### 2. Dimension Signatures

Dimension signatures are narrow normalized structures. The initial dimensions should follow `PLAN__consider_specific_signatures.md`:

- `parent_relationship`
  - `has_children`
  - `ordered_children`
- `object_definition`
  - applies to parent objects and child objects;
  - includes `object_type`, `typeOfResource` when observed, `has_parent`, `has_children`, `is_ordered`, `datastream_ids`, and datastream MIME details when available;
- `open_access`
  - includes `license` and `current_embargo_status`, with explicit `unknown` values when public API evidence is insufficient;
- `visibility`
  - initially `visibility_scope: public_api_observed`;
- `auxiliary_relationships`
  - `has_derivations`
  - `has_transcripts`
  - `has_translations`
  - `has_annotations`
- `children`
  - represents the sorted unique object-definition signatures observed among a parent item's direct children;
  - includes child object-definition signature hashes;
  - does not include child display labels;
  - does not include exact child counts.

Each dimension signature should have:

- deterministic `signature_hash` calculated from the machine-readable `signature` only;
- a generated or stable label;
- an observed-behavior description where feasible;
- up to three exemplar PIDs;
- counts useful for ranking/reporting.

The parent and child object-definition signatures can share the same builder and YAML file. Use `has_parent`, `has_children`, and `is_ordered` to distinguish context rather than creating separate parent-object and child-object signature types.

### Children Signature

The composite needs a stable way to represent the set of observed child object definitions for a parent. Implement this as its own signature type and YAML file:

```text
specifications/children_signatures.yaml
```

Recommended initial implementation:

- build individual `object_definition` dimension signatures for child docs;
- collect the unique child object-definition signature hashes observed for one parent;
- sort those hashes deterministically;
- build a `children` signature from that sorted list;
- write observed children signatures to `specifications/children_signatures.yaml`;
- include counts, count buckets, labels, and exemplar child PIDs as evidence/report metadata, not as default children-signature identity.

Child display labels such as `rel_display_label_ssi` should not be part of children-signature identity.

### 3. Composite Architecture Signature

A composite architecture signature combines selected dimension hashes into the architecture identity.

Initial composite identity should include:

- parent relationship signature hash;
- parent object definition signature hash;
- children signature hash;
- open access signature hash;
- visibility signature hash;
- auxiliary relationship signature hash.

The composite signature should not include human-readable labels, descriptions, narratives, exemplar PIDs, exact child counts, titles, collection membership, or observation metadata unless a future decision explicitly makes one of those part of architecture identity.

Also exclude `children_truncated`, `child_sample_limit`, `total_child_count`, `observed_child_count`, sampled parent counts, and child display labels from composite identity.

## Child Object Sampling Strategy

Add a child sampling limit while preserving current behavior where possible.

### New default

- Add `--max-children-per-parent`, type `int`, default `100`.
- Treat this as the default number of child objects examined per parent item.
- Use this cap only when `--fetch-all-children` is false.

### Fetch behavior

Change `lib.sampling.fetch_children()` so it can return both docs and evidence metadata:

- child docs observed;
- `num_found` or equivalent total direct-child count from Solr;
- `children_truncated` or `children_sampled` boolean;
- `child_sample_limit` value;
- maybe `child_fetch_strategy`, initially `first` by stable sort.

The current code fetches child rows with `rows = 500` and returns `(docs, truncated)`. Replace that tuple with a small dataclass so callers cannot mix up booleans and counts.

With the new default, request `rows = normalized_rows(args.max_children_per_parent)` when not fetching all children. If `--fetch-all-children` is set, keep paginating with a safe page size such as `500`, but stop at 1,000 observed children per parent and mark the result as truncated when the API reports more than 1,000 direct children.

Use the Solr `numFound` value to set truncation:

- `total_found > observed_count` means `children_truncated: true`;
- `total_found <= observed_count` means `children_truncated: false`;
- if `--fetch-all-children` is true and all pages completed, `children_truncated: false`.

Validate `--max-children-per-parent` as a positive integer. When `--fetch-all-children` is not set, the value must not exceed 1,000. When `--fetch-all-children` is set, the effective max is always 1,000; update help text so users understand that the flag means "fetch up to the 1,000-child safety cap."

### Ordering

Keep the existing child sort logic:

- paginated children first, sorted naturally by `rel_has_pagination_ssim`;
- then unordered children by PID.

For an initial implementation, the child sample can be the first `N` docs from the query result sorted by PID, then normalized with `child_sort_key`. If better ordered-child sampling is needed later, add it explicitly rather than hiding that policy in the signature builder.

Because this means a capped sample is based on `pid asc` before local `child_sort_key` ordering, reports should call the strategy `first_by_pid_then_bdr_child_sort` or similar. Do not describe capped child evidence as a representative random sample.

## API Fields To Use And Possibly Expand

Current top-level item search fields include:

- `pid`
- `primary_title`
- `object_type`
- `datastreams_ssi`
- `rel_has_part_ssim`
- `rel_is_part_of_ssim`
- `rel_is_member_of_ssim`
- `rel_is_derivation_of_ssim`
- `rel_has_description_ssim`
- `rel_has_pagination_ssim`

Current child search fields include:

- `pid`
- `primary_title`
- `object_type`
- `datastreams_ssi`
- `rel_has_pagination_ssim`
- `rel_is_derivation_of_ssim`
- `rel_is_transcript_of_ssim`
- `rel_is_translation_of_ssim`
- `rel_display_label_ssi`

Use these known public/Solr fields where available:

- `mods_type_of_resource` for `typeOfResource`;
- rights/access-control fields from rightsMetadata where publicly returned, including `*_access_*_ssim`, `_display_public_bsi`, `_display_brown_bsi`, and `_display_private_bsi`;
- MODS access-condition fields when publicly returned:
  - `mods_access_condition_use_text_tsim`;
  - `mods_access_condition_use_link_ssim`;
  - `mods_access_condition_rights_text_tsim`;
  - `mods_access_condition_rights_link_ssim`;
  - `mods_access_condition_restriction_text_tsim`;
- embargo fields `rel_pso_status_ssi` and `rel_embargo_years_ssim`;
- annotation relationship field `rel_is_annotation_of_ssim`;
- item API annotation data under `relations.hasAnnotation`, if item API calls are added for richer relationship evidence;
- derivation, transcript, and translation relationships on both parent and child records.

Embargo evidence is only partly observable through public data. Treat `rel_pso_status_ssi` and `rel_embargo_years_ssim` as recorded status/year evidence, not as a computed answer to whether the object is currently embargoed on the scan date.

Annotation relationships are publicly observable when access allows the related records to be returned. The item API scrubs private access fields inside relations but does not remove the relationship itself.

If a field is not reliably available from the public API, emit explicit `unknown` or `not_observed` values rather than over-interpreting absence.

Known current field lists are hard-coded in `lib.sampling.search_top_level_items()` and `lib.sampling.fetch_children()`. Add any new fields there first, and rely on the existing cache key's request params to separate old and new cached field lists.

## Proposed Module Changes

### `main.py`

Keep `main()` as-is structurally.

Update `parse_args()`:

- change `--sleep-seconds` default to `2.0`;
- add `--max-children-per-parent`, type `int`, default `100`;
- add `--output-specifications-dir`, defaulting to `specifications`;
- do not add a `--write-specifications` flag. Specification YAML files are a core output of this tool and should be written by default;
- update `--fetch-all-children` help text to explain that it fetches direct children up to the 1,000-child safety cap;
- preserve existing flags unless there is a strong reason to rename one.

Also update README's expanded default command and `tests/test.py::build_args()` after these argument changes.

### `lib/config.py`

If defaults are centralized there, add constants for:

- default sleep seconds, if not already centralized;
- default max children per parent;
- max children hard cap, recommended name `MAX_CHILDREN_PER_PARENT_CAP`, value `1000`;
- default specifications directory;
- increment `SCRIPT_VERSION` if state/cache compatibility should distinguish the new scan semantics.
- add a separate `SIGNATURE_ARCHITECTURE_VERSION`, recommended value `2`, for state material parameters and output metadata. This is clearer than relying only on script version.

### `lib/sampling.py`

Add a return object or dataclass for child fetch results, for example `ChildFetchResult`:

- `docs: list[dict[str, Any]]`
- `total_found: int`
- `observed_count: int`
- `truncated: bool`
- `sample_limit: int`
- `hard_limit: int`
- `fetch_all_children: bool`
- `fetch_strategy: str`

Then update callers to use the new structure.

Keep request caching through `ApiClient.search()`.

### `lib/signatures.py`

Refactor this module around dimension builders while preserving reusable helpers:

- keep deterministic hashing logic;
- keep datastream parsing/normalization, but extend it so object-definition signatures can include both `datastream_ids` and optional `datastream_details`;
- add `build_parent_relationship_signature()`;
- add `build_object_definition_signature()`;
- add `build_open_access_signature()`;
- add `build_visibility_signature()`;
- add `build_auxiliary_relationships_signature()`;
- add `build_composite_architecture_signature()`;
- add a top-level `build_signature_bundle()` or similarly named function that returns all hashes and normalized structures for one parent observation.

The current `build_item_signature()` can either become a compatibility wrapper or be replaced by the new bundle builder. If compatibility is easy, keeping a wrapper may reduce disruption in tests and reports.

Recommended concrete return shape:

```text
SignatureBundle
  observation:
    collection_pid
    parent_pid
    child_total_found
    child_observed_count
    child_sample_limit
    children_truncated
    fetch_all_children
    visibility_scope
  dimensions:
    parent_relationship
    parent_object_definition
    child_object_definitions
    children
    open_access
    visibility
    auxiliary_relationships
  composite:
    signature_hash
    signature
    component_hashes
```

This can be implemented as plain dictionaries first if that matches the surrounding code better than dataclasses.

Preserve existing helper behavior where possible:

- `hash_signature()` remains the canonical deterministic hash helper.
- `parse_datastreams()` can stay as a token helper, but add a separate helper if structured datastream details are needed.
- `count_bucket()` remains useful for reporting child evidence, but exact counts and count buckets should remain evidence/report metadata unless explicitly chosen as identity later.
- MIME details should be included in object-definition identity by default. The current `--include-mime-types` flag can either be removed, retained as a compatibility no-op, or renamed only if there is a clear need to suppress MIME details.

### `lib/models.py`

Replace or extend `ArchitectureIndex` so it can index:

- composite architecture candidates;
- dimension signature candidates by signature type;
- exemplar parent PIDs and child PIDs;
- collection examples;
- total sampled parent items;
- appearance/dominance by collection.

A possible shape:

```text
SignatureIndex
  dimension_candidates:
    parent_relationship: {...}
    object_definition: {...}
    children: {...}
    open_access: {...}
    visibility: {...}
    auxiliary_relationships: {...}
  composite_candidates: {...}
```

Keep collection classification centered on composite architecture hashes, because that best preserves the current meaning of `uniform`, `mostly_uniform`, and `mixed`.

Recommended state-backed keys:

- `composite_architecture_candidates` for the replacement architecture index;
- `dimension_signature_candidates` for grouped dimension entries;
- do not keep `common_architecture_candidates` unless implementation review finds a current internal use that still needs it. The new state can make a clean break from old coarse-signature keys.

### `lib/sampler.py`

Keep the orchestration pattern.

For each selected collection:

1. Fetch sampled top-level parent docs.
2. For each parent doc, fetch up to `--max-children-per-parent` child docs unless `--fetch-all-children` is set.
3. Build a signature bundle.
4. Add dimension signatures and composite signature to the index.
5. Save parent-level signature result in state.
6. Classify the collection using composite hashes.
7. Save progress after each parent and collection.

The state key currently named `parent_item_signature_hashes` should become `parent_item_signature_results`. Each parent result should at least include:

- `composite_signature_hash`;
- dimension hashes used by the composite;
- observation metadata needed to understand sampling/truncation;
- enough minimal labels/counts for resume without recomputing already-checked parents.

To avoid silent incompatible resumes, update state compatibility or schema versioning before changing sampler writes.

### `lib/state.py`

Update state initialization and compatibility checks.

Recommended approach:

- add or increment a state schema/version value;
- include `max_children_per_parent` and new signature mode/spec version in material parameters;
- include `signature_architecture_version` in material parameters;
- preserve existing `refresh-state`, `no-resume`, and checked-progress behavior;
- make incompatible old state fail clearly with a message instructing the user to use `--refresh-state` or a new state file.

Do not try to migrate old coarse-signature state automatically unless implementation proves trivial. The new signature semantics are materially different.

Suggested new-state fields:

```text
signature_architecture_version: 2
parent_item_signature_results: {}
dimension_signature_candidates: {}
composite_architecture_candidates: {}
```

Old fields such as `parent_item_signature_hashes` and `common_architecture_candidates` can be absent in new state.

### `lib/classification.py`

Keep classification behavior largely unchanged, but rename internal variables as needed:

- use composite architecture hashes as the values being counted;
- keep `min_sample_size` and `min_consistency_percent` semantics;
- keep output labels: `uniform`, `mostly_uniform`, `mixed`, `insufficient_sample`.

### `lib/report.py`

Update JSON and Markdown output to show the new model.

JSON should include:

- run timestamp;
- API root;
- material parameters;
- collection summaries;
- composite architecture candidates;
- dimension signature candidates;
- warnings;
- state/evidence metadata relevant to interpreting child sampling.

Markdown should include:

- summary counts;
- most common composite architecture signatures;
- component dimension labels/hashes for each composite;
- parent relationship summary;
- parent object definition summary;
- children signature summary;
- open access, visibility, and auxiliary relationship summaries;
- example collections and items;
- mixed collections.

The report should make capped child sampling obvious so a reviewer does not mistake a 100-child sample for complete evidence.

Use output names that make the semantic shift explicit:

- prefer `composite_architectures` as the JSON/report key for composite architecture candidates;
- include `dimension_signatures` beside it;
- add top-level `signature_architecture_version`;
- add top-level `child_sampling` summary with default limit, total truncated parent observations, and fetch strategy.

### New `lib/specifications.py`

Add a new module for writing YAML specification files, or for building specification-ready data structures if direct writing is deferred.

Responsibilities:

- group observed dimension signatures by signature type;
- group observed children signatures;
- group observed composite architecture signatures;
- attach generated descriptions and up to three exemplar PIDs;
- write flat files directly under `specifications/`:
  - `parent_relationship_signatures.yaml`
  - `object_definition_signatures.yaml`
  - `open_access_signatures.yaml`
  - `visibility_signatures.yaml`
  - `auxiliary_relationships_signatures.yaml`
  - `children_signatures.yaml`
  - `composite_architecture_signatures.yaml`
- merge with existing YAML files when they already exist and were derived from the same API root/signature version. Because identifiers are deterministic hashes rather than newly generated UUIDs, existing entries with the same hash should be updated or enriched instead of duplicated.

Dependency decision:

- The project currently does not list a YAML package in `pyproject.toml`.
- Add a YAML dependency rather than hand-writing YAML. `PyYAML` is acceptable; a package that also supports schema validation is also acceptable if it stays simple.
- Validate the generated data structures in tests before writing YAML.

## Specification File Semantics

Each YAML file should have this top-level shape:

```yaml
schema_version: 1
signature_type: parent_relationship
signatures:
  some_stable_label:
    signature_hash: abc123def456
    description: Human-readable observed-behavior description.
    exemplar_pids:
      - bdr:example
    observed_count: 123
    signature:
      has_children: true
      ordered_children: false
```

Labels should be stable enough for review, but the hash should be the true machine identifier.

Hash inputs should exclude:

- `signature_hash`;
- label keys;
- descriptions;
- narratives;
- exemplar PIDs;
- observed counts;
- collection counts;
- titles;
- exact PIDs;
- timestamps;
- scan settings;
- child truncation metadata;
- child display labels.

Hash inputs should include only the normalized `signature` structure for a dimension, or the normalized set of component hashes for a composite.

## Output And CLI Design

Specification YAML files are the core output of this tool and should be written during normal runs.

Add `--output-specifications-dir specifications` and write YAML files after the JSON/Markdown reports are built. There should be no opt-out flag.

Generated specification files should be treated as durable, build-out-over-time artifacts, not disposable scan scratch files. When a specification file already exists and was derived from the same API root and compatible signature architecture version, merge new observed signatures into it:

- keep existing entries keyed by deterministic `signature_hash`;
- add new entries for previously unseen hashes;
- enrich existing entries with new exemplar PIDs or observed counts where appropriate;
- preserve any human-entered description/status fields when possible;
- avoid duplicating entries with the same hash.

Operational state can remain JSON or another internal format. Only the specification files need to be YAML.

## State And Cache Compatibility

### Cache

Keep the current API response cache. New or changed request params naturally produce new cache files.

Consider incrementing `SCRIPT_VERSION` if the implementation wants to avoid reusing old cached responses after field-list changes. This may not be strictly required because `fl`, `rows`, `start`, and `q` are already part of the cache key through params.

### State

State compatibility must change. Add `max_children_per_parent` and signature architecture version to material parameters. Old state based on coarse signatures should not resume silently into new dimension/composite signature runs.

Recommended state behavior:

- old state with no signature architecture version should raise a clear compatibility error;
- `--refresh-state` should start fresh while still allowing cached API responses to be reused;
- `--refresh-cache` should remain independent of state refresh.

## Testing Plan

Use `unittest` and run through `uv run ./run_tests.py`.

Add or update tests for:

- deterministic hashing excludes descriptions/examples and includes only signature identity fields;
- parent relationship signature detects no children, unordered children, and ordered children;
- object definition signature normalizes datastream IDs and optional MIME details;
- child sampling returns `truncated` when total children exceed `--max-children-per-parent` and `--fetch-all-children` is false;
- child sampling with `--fetch-all-children` fetches through all pages up to the 1,000-child safety cap;
- composite signatures are stable combinations of component hashes;
- collection classification still works using composite hashes;
- state compatibility rejects old coarse-signature state or mismatched child sampling settings;
- Markdown report clearly shows component signatures and child evidence limits;
- YAML specification output has the expected top-level structure.
- YAML specification output merges with existing same-API/same-version entries without duplicating deterministic hashes.
- `--fetch-all-children` stops at the 1,000-child safety cap and marks truncation when more children exist.

## Implementation Sequence

### Phase 1: Preserve behavior while adding child cap

- Add `--max-children-per-parent 100`.
- Change `--sleep-seconds` default to `2.0`.
- Update `fetch_children()` to cap default child inspection at 100 and return evidence metadata.
- Update state material parameters and tests.
- Ensure current JSON/Markdown reports still run with minimal shape changes.
- Explicitly remove truncation from architecture identity when the new signature bundle is introduced; until then, avoid expanding reliance on the old `children_truncated` hash behavior.

### Phase 2: Build dimension signature bundle

- Add dimension signature builder functions in `lib.signatures`.
- Reuse current datastream parsing and hash helpers.
- Build a `signature_bundle` for each parent item.
- Include parent relationship, parent object definition, children, open access, visibility, and auxiliary relationships.
- Keep all unknown public-API fields explicit rather than inferred.

### Phase 3: Replace coarse architecture indexing with composite indexing

- Update `ArchitectureIndex` or introduce a new index model.
- Count composite architecture signatures for collection classification.
- Accumulate dimension signature candidates separately.
- Save parent signature bundle results in state.
- Maintain example item and collection behavior.

### Phase 4: Update reports

- Update JSON output to expose composite and dimension candidates.
- Update Markdown output to explain each composite through component signatures.
- Highlight child sampling limits and truncation in report text.
- Keep report filters such as `--top-architectures` and `--include-singletons` working for composite architectures.

### Phase 5: Generate specification YAML files

- Add `lib.specifications`.
- Add output directory for specification writing.
- Write flat YAML files under `specifications/`.
- Include stable hashes, descriptions, exemplar PIDs, observed counts, and signature structures.
- Merge deterministic-hash entries into existing specification YAML files when the API root and signature version are compatible.
- Add tests for YAML/specification structures.

### Phase 6: Documentation and validation

- Update `README.md` only after implementation is working.
- Document new defaults and flags.
- Run smoke scans with small limits before larger scans.
- Run full tests with `uv run ./run_tests.py`.

## Suggested Smoke Commands After Implementation

Small cached public-API run:

```bash
uv run ./main.py \
  --max-collections 1 \
  --max-items-per-collection 3 \
  --max-children-per-parent 5 \
  --rows 5 \
  --sleep-seconds 2 \
  --output-json /tmp/bdr_specific_signatures.json \
  --output-md /tmp/bdr_specific_signatures.md \
  --state-file /tmp/bdr_specific_signatures_state.json
```

Targeted specification-writing run:

```bash
uv run ./main.py \
  --collection-pids bdr:example_collection \
  --max-items-per-collection 10 \
  --max-children-per-parent 10 \
  --output-specifications-dir specifications \
  --refresh-state
```

Full default run after confidence improves:

```bash
uv run ./main.py
```

The expanded default command should eventually document:

```bash
uv run ./main.py \
  --api-root https://repository.library.brown.edu/api/ \
  --max-collections 20 \
  --max-items-per-collection 100 \
  --max-children-per-parent 100 \
  --rows 100 \
  --sleep-seconds 2.0
```

## Risks And Mitigations

- More child requests may increase public API load.
  - Mitigate with `--sleep-seconds 2.0`, child caps, caching, and small smoke scans.
- Public API fields may not expose license, embargo, `typeOfResource`, or annotation evidence consistently.
  - Mitigate with explicit `unknown` values and warnings rather than inferred false values.
- Old state files may appear compatible but contain outdated coarse signatures.
  - Mitigate with explicit signature architecture versioning in state material parameters.
- YAML specification files could be mistaken for curated policy.
  - Mitigate descriptions that say they document observed behavior, plus optional human-entered status fields in later work.
- Child sampling may hide variation among later children.
  - Mitigate by recording `total_found`, observed count, sample limit, and truncation status in observation metadata and reports.
- Merging generated YAML with existing curated entries could accidentally overwrite human notes.
  - Mitigate by preserving existing human-entered fields and only updating deterministic/generated fields for matching hashes.

## Open Decisions For Implementation Session

- Whether to use `PyYAML` plus structural validation tests, or a YAML package that includes schema validation.
- Whether existing `--include-mime-types` should be removed, retained as a compatibility no-op, or changed into a different advanced flag.
- Whether item API calls are worth adding for richer `relations.hasAnnotation` evidence, or whether the first implementation should rely only on Search API fields.
- Which existing human-entered fields in YAML files must be preserved during merge beyond description/status/narrative notes.


## Questions / Decision Points For Birkin

No user-blocking questions remain before implementation. The open decisions above can be resolved during implementation with conservative choices and noted in the final implementation summary.

## Recommended Initial Assumptions

Unless implementation review finds contradictory evidence, assume:

- Public API sampling is the visibility scope.
- Missing rights/embargo fields mean `unknown`, not false or unrestricted.
- Exact child counts do not define architecture identity.
- Children signatures are built from sorted unique child object-definition signature hashes.
- Child count buckets and observed child object definition groups can support review without becoming identity.
- MIME details are part of object-definition identity by default.
- Child display labels are evidence/report context only, not signature identity.
- Composite architecture hashes are the replacement for the current coarse architecture hashes.
- Existing cache and state mechanisms should be extended, not rewritten.
