# Plan: determine common BDR object architectures

## Table Of Contents

- [Purpose](#purpose)
- [Reviewed Context](#reviewed-context)
- [Recommendation](#recommendation)
- [Proposed Script Name](#proposed-script-name)
- [Inputs And Configuration](#inputs-and-configuration)
- [Data Retrieval Strategy](#data-retrieval-strategy)
- [Architecture Signature Design](#architecture-signature-design)
- [Collection Consistency Logic](#collection-consistency-logic)
- [Cross-Collection Architecture Bucketing](#cross-collection-architecture-bucketing)
- [Output Files](#output-files)
- [Implementation Modules](#implementation-modules)
- [API Request Details](#api-request-details)
- [Caching](#caching)
- [Resumable Run State](#resumable-run-state)
- [Rate Limiting And Operational Safety](#rate-limiting-and-operational-safety)
- [Edge Cases](#edge-cases)
- [Sampling Strategy](#sampling-strategy)
- [Architecture Labels](#architecture-labels)
- [Validation Plan](#validation-plan)
- [Open Questions](#open-questions)
- [Proposed Initial Milestone](#proposed-initial-milestone)
- [Pseudocode](#pseudocode)
- [Notes For Future Implementation](#notes-for-future-implementation)
- [Addendum: Separate Architecture Identity From Observation Metadata](#addendum-separate-architecture-identity-from-observation-metadata)

## Purpose

Develop a script that identifies common object architectures in the Brown Digital Repository so future ingesters can see which parent/child/datastream patterns are already common and supported without custom development.

The reason for this is so we can document and share with future ingesters the standard architectures that we know work and are supported without custom development.

Original thought...

I'm thinking it might be possible to use the BDR-APIs to:
- find all collections
- sort them by largest-to-smallest
- go through each doing the following:
    - get a list of the items for the collection
    - go through each doing the following:
        - determine parent-child relationships
        - determine the datastreams for the parent
        - determine the datastreams for each child
- if all the parent-child-relationships are the same -- or the first 100 are -- add that to the bucket of common-architectures.
- stop after 20 collections (multiple collections might have the same architecture)


## Reviewed Context

Local files reviewed:

- `bdr_ecosystem_project/AGENT_info/bdr_apis_project__AGENT_INDEX.yaml`
- `bdr_ecosystem_project/AGENT_info/bdr_solr_conf__AGENT_INDEX.yaml`
- `bdr_ecosystem_project/bdr_repos/bdr_apis_project/items_app/access_models.py`
- `bdr_ecosystem_project/bdr_repos/bdr_apis_project/folders_app/models.py`
- `bdr_ecosystem_project/bdr_repos/bdr_apis_project/search_app/models.py`
- `bdr_ecosystem_project/bdr_repos/bdr_apis_project/search_app/utility_code.py`
- `bdr_ecosystem_project/bdr_repos/bdr_apis_project/bdr_apis_common/solr.py`

External docs reviewed:

- BDR API documentation wiki home
- BDR API overview
- Item API examples
- Collection API examples
- Search API examples

Important findings:

- Public API responses are JSON.
- Public item API endpoint shape: `https://repository.library.brown.edu/api/items/<pid>/`.
- Public collection API endpoint shape: `https://repository.library.brown.edu/api/collections/<collection-id>/`.
- Public search API endpoint shape: `https://repository.library.brown.edu/api/search/?<search-query>`.
- Search API accepts Solr-style query syntax, `rows`, `start`, and `fl`.
- The public docs show collection membership queries using `rel_is_member_of_collection_ssim:"<collection-pid>"`.
- The public docs show top-level collection listing at `/api/collections/`.
- The public docs warn that Cloudflare Bot Protection was added in Spring 2025 and may affect high-volume API users.
- In the API code, item read responses are Solr-centric and then enriched with `relations`, `links`, `datastreams`, and brief metadata.
- In the API code, item relation expansion searches for related objects via fields such as:
  - `rel_is_part_of_ssim`
  - `rel_is_member_of_ssim`
  - `rel_is_derivation_of_ssim`
  - `rel_is_annotation_of_ssim`
  - `rel_dcterms_is_version_of_ssim`
  - `rel_is_transcript_of_ssim`
  - `rel_is_translation_of_ssim`
- Child ordering in API responses is based on `rel_has_pagination_ssim` when present, with natural sorting, and then PID sorting for unordered children.
- Datastream inventory is indexed in Solr as `datastreams_ssi`, a JSON string. The item API exposes this as parsed `datastreams` in full item responses.
- The Search API caps requested `rows` at `MAX_ROWS`, which is `500` in the public search code.
- The direct internal Solr helper can use `DEFAULT_SOLR_ROWS_COUNT`, but this script should assume public Search API behavior unless run from a trusted internal environment.

## Recommendation

Build the script around the Search API, not primarily the Collection API or full Item API.

The Collection API is useful for getting collection metadata and links, but the Search API is better for bulk discovery because it supports:

- collection membership queries
- field-limited responses via `fl`
- pagination via `start`
- row-size control via `rows`
- Solr fields needed for architecture detection

Use the full Item API only in an optional validation/enrichment mode, because full item API calls expand relations and collection data and can be much more expensive at scale.

## Proposed Script Name

Possible path:

```text
bdr_ecosystem_project/misc/determine_common_bdr_architectures.py
```

If the script will eventually be copied into a production-adjacent repo, keep paths and configuration generic and avoid hardcoded references to `bdr_ecosystem_project`.

## Inputs And Configuration

Support command-line options:

```text
--api-root https://repository.library.brown.edu/api/
--max-collections 20
--max-items-per-collection 100
--rows 100
--sleep-seconds 0.25
--output-json common_architectures.json
--output-md common_architectures.md
--cache-dir .architecture_cache
--state-file .architecture_cache/run_state.json
--refresh-cache
--refresh-state
--no-resume
--include-private false
--full-item-validation-sample 0
--collection-query-mode public-top-level
```

Defaults:

- `api-root`: `https://repository.library.brown.edu/api/`
- `max-collections`: `20`
- `max-items-per-collection`: `100`
- `rows`: `100`, safely below the Search API cap of `500`
- `sleep-seconds`: at least `0.25`, because the public wiki warns about Cloudflare Bot Protection for high-rate API traffic
- cache enabled by default
- state/resume file enabled by default
- full item validation disabled by default

Useful optional tuning:

- `--min-consistency-percent 90`
  - classify a collection as internally consistent if at least 90% of sampled top-level items share the same architecture signature
- `--top-architectures 25`
  - limit report output
- `--include-singletons`
  - include architectures seen only once
- `--collection-pids bdr:abc,bdr:def`
  - bypass top-collection discovery and inspect specific collections
- `--skip-collections bdr:abc,bdr:def`
  - ignore known special-purpose or pathological collections

## Data Retrieval Strategy

### 1. Discover collections

Preferred public approach:

1. Call the Collection API top-level endpoint:

   ```text
   GET /api/collections/
   ```

2. Extract collection PIDs and names.

3. For each collection PID, count member top-level items using Search API.

If `/api/collections/` does not include enough collections or does not expose item counts, use the Search API directly:

```text
GET /api/search/?q=object_type:bdr-collection&fl=pid,collection_name_ssim&rows=500&start=0
```

For only top-level collections:

```text
q=object_type:bdr-collection AND -rel_is_member_of_collection_ssim:*
```

Implementation note:

- The public `/api/search/` endpoint applies public discover access.
- If the script runs internally and needs private objects, add an explicit internal mode instead of silently mixing public and private results.

### 2. Count collection items

For each collection:

```text
q=rel_is_member_of_collection_ssim:"<collection-pid>" AND -rel_is_part_of_ssim:* AND -object_type:bdr-collection
fl=pid
rows=0
```

Use `response.numFound` as the top-level item count.

Rationale:

- `rel_is_member_of_collection_ssim` identifies collection membership.
- `-rel_is_part_of_ssim:*` excludes child objects so the collection size reflects top-level object architectures.
- `-object_type:bdr-collection` excludes subcollections.

Sort collections largest-to-smallest by this count.

### 3. Sample top-level items in each collection

For each selected collection, page through up to `max-items-per-collection` top-level item records:

```text
q=rel_is_member_of_collection_ssim:"<collection-pid>" AND -rel_is_part_of_ssim:* AND -object_type:bdr-collection
fl=pid,primary_title,object_type,datastreams_ssi,rel_has_part_ssim,rel_is_part_of_ssim,rel_is_member_of_ssim,rel_is_derivation_of_ssim,rel_has_description_ssim,rel_has_pagination_ssim
rows=<rows>
start=<offset>
sort=pid asc
```

Field caveat:

- The API implementation definitely uses `rel_is_part_of_ssim` to find children.
- It may not expose or need `rel_has_part_ssim` for parent records.
- The script should not require parent-side `hasPart` fields. It should derive children by querying `rel_is_part_of_ssim:"<parent-pid>"`.

### 4. Fetch children for each sampled top-level item

For each parent PID, query children:

```text
q=rel_is_part_of_ssim:"<parent-pid>"
fl=pid,primary_title,object_type,datastreams_ssi,rel_has_pagination_ssim,rel_is_derivation_of_ssim,rel_is_transcript_of_ssim,rel_is_translation_of_ssim,rel_display_label_ssi
rows=500
sort=pid asc
```

Then sort in the script using the API's logic:

1. Children with `rel_has_pagination_ssim[0]` first, using natural sort.
2. Children without pagination next, sorted by PID.

If a parent has more than 500 children:

- record `children_truncated: true`
- fetch additional pages if `--fetch-all-children` is set
- otherwise classify with a truncated marker so the result is not mistaken for a complete architecture

### 5. Optional relation enrichment

For each parent or child, optionally query additional relation classes if the architecture definition should include them:

- derivations:

  ```text
  q=rel_is_derivation_of_ssim:"<pid>"
  ```

- transcripts:

  ```text
  q=rel_is_transcript_of_ssim:"<pid>"
  ```

- translations:

  ```text
  q=rel_is_translation_of_ssim:"<pid>"
  ```

- annotations:

  ```text
  q=rel_is_annotation_of_ssim:"<pid>"
  ```

Recommendation:

- Version 1 should include direct children and datastream inventory only.
- Add derivation/transcript/translation/annotation counts as secondary metadata, not as part of the primary architecture signature, unless the intended documentation explicitly treats those as core object architecture.

## Architecture Signature Design

The signature should be stable, compact, and not dependent on PIDs or titles.

### Normalize datastreams

From `datastreams_ssi`, parse JSON and keep only datastream IDs by default:

```json
{
  "MODS": {},
  "RELS-EXT": {},
  "rightsMetadata": {},
  "JP2": {"mimeType": "image/jp2"},
  "thumbnail": {"mimeType": "image/jpeg"}
}
```

Normalize to:

```text
["JP2", "MODS", "RELS-EXT", "rightsMetadata", "thumbnail"]
```

Optionally include MIME type with `--include-mime-types`:

```text
JP2:image/jp2
thumbnail:image/jpeg
```

Default recommendation:

- Include datastream IDs.
- Exclude MIME type from primary signature.
- Report MIME-type variation separately.

Reason:

- Datastream IDs describe the supported object architecture.
- MIME types are useful diagnostics but may fragment otherwise equivalent architectures.

### Parent shape

Represent the parent as:

```json
{
  "object_type": "implicit-set",
  "datastreams": ["MODS", "RELS-EXT", "rightsMetadata"],
  "child_count_bucket": "many",
  "child_groups": [...]
}
```

Use child count buckets rather than exact counts in the primary signature:

- `none`
- `one`
- `few:2-9`
- `many:10+`

Exact child counts should still be reported as metrics.

Reason:

- A 20-page and 200-page scanned book have the same useful architecture.
- Exact child counts would make common architectures look artificially unique.

### Child shape

Group children by normalized child type and datastream set:

```json
{
  "object_type": "image",
  "datastreams": ["JP2", "MODS", "RELS-EXT", "rightsMetadata", "thumbnail"],
  "display_label": "page-image",
  "count_bucket": "many"
}
```

For common compound objects, this avoids listing every page. A 100-page item becomes:

```text
parent implicit-set [MODS,RELS-EXT,rightsMetadata]
  many image children [JP2,MODS,RELS-EXT,rightsMetadata,thumbnail]
```

### Mixed child shapes

If a parent has mixed children, represent each group:

```text
parent implicit-set [MODS,RELS-EXT,rightsMetadata]
  many image children [JP2,MODS,RELS-EXT,rightsMetadata,thumbnail]
  one pdf child [PDF,RELS-EXT,rightsMetadata]
  one tei child [TEI,RELS-EXT,rightsMetadata]
```

Sort child groups by:

1. object type
2. display label
3. datastream tuple

### Signature serialization

Use deterministic JSON for machine grouping:

```python
signature_key = json.dumps(signature, sort_keys=True, separators=(",", ":"))
signature_hash = hashlib.sha256(signature_key.encode("utf-8")).hexdigest()[:12]
```

Store both:

- `signature_hash`
- `signature`

## Collection Consistency Logic

For each collection:

1. Build an architecture signature for each sampled top-level item.
2. Count signatures.
3. Determine the dominant signature.
4. Compute:

```text
dominant_count / sampled_count
```

Classify:

- `uniform`
  - 100% of sampled items share the same signature
- `mostly_uniform`
  - at least `min-consistency-percent`, default 90%
- `mixed`
  - below threshold
- `insufficient_sample`
  - fewer than a configured minimum, e.g. 5 sampled items

The original idea says "if all the parent-child relationships are the same, or the first 100 are." Prefer:

- sample up to 100 top-level items by default
- use `dominant_signature_percent`
- report both exact and thresholded results

This keeps the script honest when collection 1 has 98 matching items and 2 exceptions.

## Cross-Collection Architecture Bucketing

After processing collections:

1. Merge all item-level signatures across collections.
2. Count total sampled items per signature.
3. Count collections where each signature is dominant.
4. Count collections where each signature appears at all.
5. Record representative examples:

```json
{
  "signature_hash": "abc123...",
  "total_sampled_items": 824,
  "dominant_in_collections": 7,
  "appears_in_collections": 10,
  "example_items": [
    {"pid": "bdr:...", "title": "...", "collection_pid": "bdr:..."}
  ],
  "example_collections": [
    {"pid": "bdr:...", "name": "..."}
  ]
}
```

Sort architecture report by:

1. `dominant_in_collections` descending
2. `total_sampled_items` descending
3. `appears_in_collections` descending

## Output Files

### JSON output

Primary machine-readable output:

```json
{
  "generated_at": "2026-05-22T...",
  "api_root": "https://repository.library.brown.edu/api/",
  "parameters": {},
  "collections_considered": [],
  "architectures": [],
  "warnings": []
}
```

Per collection:

```json
{
  "pid": "bdr:...",
  "name": "...",
  "top_level_item_count": 1234,
  "sampled_item_count": 100,
  "dominant_signature_hash": "abc123...",
  "dominant_signature_percent": 0.97,
  "classification": "mostly_uniform",
  "signature_counts": [
    {"signature_hash": "abc123...", "count": 97},
    {"signature_hash": "def456...", "count": 3}
  ],
  "warnings": []
}
```

Per architecture:

```json
{
  "signature_hash": "abc123...",
  "label": "implicit-set with image page children",
  "signature": {},
  "dominant_in_collections": 7,
  "appears_in_collections": 10,
  "total_sampled_items": 824,
  "example_collections": [],
  "example_items": []
}
```

### Markdown output

Human-readable report:

```md
# Common BDR Object Architectures

Generated: ...

## Summary

- Collections scanned: 20
- Top-level items sampled: 2,000
- Unique architectures observed: 14
- Uniform collections: 12
- Mostly uniform collections: 4
- Mixed collections: 4

## Most Common Architectures

### 1. implicit-set with image page children

- Signature: `abc123...`
- Dominant in collections: 7
- Sampled items: 824
- Parent:
  - object_type: `implicit-set`
  - datastreams: `MODS`, `RELS-EXT`, `rightsMetadata`
- Children:
  - many `image` children with `JP2`, `MODS`, `RELS-EXT`, `rightsMetadata`, `thumbnail`
- Example collections:
  - ...
- Example items:
  - ...
```

Include a final section:

```md
## Collections With Mixed Architectures
```

These are useful because they may represent:

- intentionally mixed content
- legacy ingest variation
- bad sampling
- collection-level grouping that is not architecture-specific

## Implementation Modules

Suggested internal functions/classes:

```python
@dataclass
class ApiClient:
    api_root: str
    session: httpx.Client
    sleep_seconds: float
    cache: Cache

    def search(self, params: dict) -> dict: ...
    def get_collection(self, pid: str) -> dict: ...
    def get_item(self, pid: str, fl: str | None = None) -> dict: ...
```

Keep Python-version compatibility in mind if copying into older BDR repos. If targeting Python 3.8, use `Optional[str]` instead of `str | None`.

Core functions:

```python
def discover_collections(client) -> list[CollectionRef]:
    ...

def count_top_level_items(client, collection_pid: str) -> int:
    ...

def fetch_top_level_items(client, collection_pid: str, limit: int) -> list[SolrDoc]:
    ...

def fetch_children(client, parent_pid: str) -> list[SolrDoc]:
    ...

def parse_datastreams(doc: dict) -> tuple[str, ...]:
    ...

def natural_sort_key(value: str) -> list:
    ...

def build_item_signature(parent_doc: dict, child_docs: list[dict]) -> dict:
    ...

def hash_signature(signature: dict) -> str:
    ...

def classify_collection(signatures: list[str], threshold: float) -> CollectionSummary:
    ...

def render_markdown_report(result: dict) -> str:
    ...
```

## API Request Details

### Search helper

Use `httpx.Client`, per this repository's coding directives.

Set an explicit user agent:

```text
BDRArchitectureSampler/0.1 (Brown University Library internal planning)
```

Use timeouts:

```python
timeout = httpx.Timeout(60.0, connect=5.0)
```

Retry only conservatively:

- retry `429`, `502`, `503`, `504`
- exponential backoff
- respect `Retry-After` if present
- do not retry `400`
- do not hammer through Cloudflare challenges

### Query encoding

Build params with `httpx`, not hand-concatenated strings:

```python
params = {
    "q": 'rel_is_member_of_collection_ssim:"bdr:wum3gm43" AND -rel_is_part_of_ssim:*',
    "fl": "pid,primary_title,object_type,datastreams_ssi",
    "rows": 100,
    "start": 0,
}
client.get(f"{api_root}search/", params=params)
```

### Pagination

For Search API:

- read `response.numFound`
- request pages with `start`
- stop when:
  - enough sample rows have been collected
  - returned docs are empty
  - start >= numFound

Remember public Search API caps `rows` at 500 in the code.

## Caching

Use a simple on-disk JSON cache:

```text
.architecture_cache/
  search_<sha256>.json
  collection_<pid>.json
  item_<pid>.json
```

Cache key should include:

- URL path
- sorted params
- script version

Add `--refresh-cache` to bypass existing files.

Reason:

- The analysis may involve thousands of repeated public API calls during development.
- Caching reduces Cloudflare/API pressure and makes debugging deterministic.

## Resumable Run State

In addition to the response cache, persist a run-state file so a network failure, process interruption, or Cloudflare-related stop can resume without losing completed analysis.

Default path:

```text
.architecture_cache/run_state.json
```

The state file should be written atomically after each meaningful unit of work:

- after collection discovery/counting
- after selecting collections
- after each checked collection
- after each checked parent item, if parent-level processing is long-running
- after architecture candidate buckets change

Use a temp file plus rename, for example `run_state.json.tmp` then `run_state.json`, so an interrupted write does not corrupt the previous state.

State should include at least:

```json
{
  "script_version": "0.1",
  "api_root": "https://repository.library.brown.edu/api/",
  "parameters": {},
  "started_at": "2026-05-22T...",
  "updated_at": "2026-05-22T...",
  "collections_discovered": [],
  "selected_collections": [],
  "checked": {
    "collection_counts": ["bdr:..."],
    "collections": ["bdr:..."],
    "parent_items": ["bdr:..."]
  },
  "parent_item_signature_hashes": {
    "bdr:...": "abc123..."
  },
  "in_progress": {
    "collection_pid": "bdr:...",
    "parent_pid": "bdr:..."
  },
  "common_architecture_candidates": {
    "abc123...": {
      "signature_hash": "abc123...",
      "signature": {},
      "total_sampled_items": 12,
      "dominant_in_collections": 1,
      "appears_in_collections": 2,
      "example_collections": [],
      "example_items": []
    }
  },
  "collection_summaries": [],
  "warnings": []
}
```

Resume behavior:

- Load `--state-file` at startup unless `--refresh-state` is passed.
- Validate that `script_version`, `api_root`, and material parameters match the current run.
- If they do not match, stop with a clear message unless `--refresh-state` is passed.
- Skip already checked collection counts, collections, and parent items.
- Rehydrate `common_architecture_candidates`, `collection_summaries`, and checked sets from state before continuing.
- Treat cache files as reusable HTTP responses and the state file as resumable analysis progress; do not rely on cache files alone to infer what has been checked.

Useful related options:

```text
--refresh-state
--no-resume
```

`--refresh-cache` should not automatically discard run state. Keep cache refresh and state refresh separate so a user can re-fetch API responses while preserving or explicitly resetting analysis progress.

## Rate Limiting And Operational Safety

Important because the public BDR API wiki warns about Cloudflare Bot Protection for high-volume API usage.

Script defaults should be intentionally gentle:

- request delay: at least 250 ms
- low `rows` default: 100
- default collection limit: 20
- default top-level item sample: 100 per collection
- no full Item API calls unless requested
- clear progress logging so the user can stop early

For production/internal use:

- consider running against an internal API endpoint or direct Solr read-only endpoint
- coordinate with BDR maintainers before full-repository scans
- keep the state/resume file enabled so long scans can continue without repeating checked work

## Edge Cases

Handle these explicitly:

- `datastreams_ssi` missing
  - classify datastreams as `[]`
  - add warning
- `datastreams_ssi` invalid JSON
  - classify as `["__INVALID_DATASTREAMS_JSON__"]`
  - add warning with PID
- child query returns more than one page
  - mark truncated unless `--fetch-all-children`
- private or undiscoverable objects
  - public API will omit or deny them; report scope as public/discoverable only
- collection contains subcollections
  - top-level item query excludes `object_type:bdr-collection`
- items are members of multiple collections
  - architecture counts can appear under multiple collections; that is acceptable
- child objects are direct collection members too
  - top-level query excludes `rel_is_part_of_ssim:*`
- unordered children
  - sort by PID after ordered children
- mixed object types in one collection
  - report as mixed rather than forcing a single architecture
- exact child counts vary
  - use count buckets in signature, exact counts in metrics
- large collections with first 100 not representative
  - support `--sample-strategy first`, `--sample-strategy evenly-spaced`, and `--sample-strategy random`

Recommended default sample strategy:

- `evenly-spaced` if `numFound` is known and large
- otherwise first page sorted by PID

Reason:

- First 100 by PID may overrepresent early ingest practices in collections that changed over time.

## Sampling Strategy

Support three strategies:

### first

Take first N records by stable sort, probably `pid asc`.

Pros:

- deterministic
- simple

Cons:

- may bias toward old ingests

### evenly-spaced

Use `numFound` and collect records at intervals across the result set.

Pros:

- better collection-wide coverage
- deterministic

Cons:

- more requests

### random

Use `random` sampling from discovered PIDs.

Pros:

- statistically useful

Cons:

- less reproducible unless seeded
- may require fetching all PIDs first

Recommendation:

- Implement `first` for the initial script.
- Add `evenly-spaced` before using the report for final documentation.

## Architecture Labels

Generate a human-friendly label from the signature:

Examples:

- `standalone image`
- `standalone pdf`
- `implicit-set with image children`
- `implicit-set with image children plus pdf child`
- `book-like object with image pages and TEI child`
- `archive/zip object`
- `streaming object`

Labeling logic:

1. If no children:
   - `standalone <object_type>`
2. If children:
   - `<parent object_type> with <child summary>`
3. Child summary:
   - if one group: `<child object_type> children`
   - if multiple: join major groups, e.g. `image children plus pdf child`

Keep labels advisory. The signature is the real grouping key.

## Validation Plan

### Unit tests

Use small fixture docs:

- standalone PDF
- standalone image
- implicit-set with three image children
- implicit-set with image children plus PDF child
- missing `datastreams_ssi`
- invalid `datastreams_ssi`
- ordered and unordered children

Test:

- datastream parsing
- natural sorting
- child grouping
- signature hashing stability
- collection consistency classification
- Markdown rendering for one sample architecture

### Integration smoke test

With network/API access:

```bash
uv run ./determine_common_bdr_architectures.py \
  --max-collections 1 \
  --max-items-per-collection 5 \
  --rows 5 \
  --sleep-seconds 1 \
  --output-json /tmp/bdr_architectures.json \
  --output-md /tmp/bdr_architectures.md
```

Check:

- no unexpected 400 responses
- `response.numFound` parsed correctly
- datastream JSON parsed
- child lookup returns plausible data
- outputs are deterministic across repeated cached runs

## Open Questions

- Should the initial scan be public-only, or should it run internally with admin identity to include private and restricted content?
- Should architecture identity include descriptive metadata datastream differences such as `MODS` vs `DWC` vs `TEI`, or should descriptive datastreams be reported separately?
- Should derivations, streams, transcripts, translations, and annotations be part of the architecture signature or secondary relationship metadata?
- Should exact child count ever be part of the signature for small objects, or should count buckets always be used?
- Should collection ranking use total top-level item count, public/discoverable count, or internal/admin count?
- Should subcollections be recursively included in a parent collection analysis, or treated as independent collections?
- Where should the final output live, and should it become an agent-info or public ingest-guidance document?

## Proposed Initial Milestone

Build a read-only prototype that:

1. Finds top-level public collections.
2. Counts top-level non-collection items per collection.
3. Selects the 20 largest collections.
4. Samples up to 100 top-level items per collection.
5. Fetches direct children for each sampled item.
6. Builds architecture signatures from:
   - parent `object_type`
   - parent datastream IDs
   - child object type groups
   - child datastream ID groups
   - child count buckets
7. Produces JSON and Markdown reports.
8. Uses cache and rate limiting by default.
9. Saves resumable state, including checked work and populated common-architecture candidates.

After reviewing prototype output, decide whether to add:

- direct internal Solr mode
- private/admin mode
- full Item API validation
- recursive subcollection handling
- derivation/transcript/translation/annotation architecture dimensions

## Pseudocode

```python
def main():
    args = parse_args()
    client = ApiClient(args)
    state = load_or_initialize_state(args)

    collections = discover_collections(client, args)
    for collection in collections:
        if state.has_checked_collection_count(collection.pid):
            continue
        collection.top_level_item_count = count_top_level_items(client, collection.pid)
        state.mark_collection_count_checked(collection)
        save_state(args.state_file, state)

    selected = sorted(collections, key=lambda c: c.top_level_item_count, reverse=True)
    selected = selected[:args.max_collections]
    state.set_selected_collections(selected)
    save_state(args.state_file, state)

    architecture_index = ArchitectureIndex.from_state(state)
    collection_summaries = state.collection_summaries

    for collection in selected:
        if state.has_checked_collection(collection.pid):
            continue
        parent_docs = fetch_sampled_top_level_items(client, collection.pid, args)
        item_signature_hashes = []

        for parent_doc in parent_docs:
            if state.has_checked_parent_item(parent_doc["pid"]):
                item_signature_hashes.append(state.get_parent_signature_hash(parent_doc["pid"]))
                continue
            child_docs = fetch_children(client, parent_doc["pid"], args)
            signature = build_item_signature(parent_doc, child_docs, args)
            signature_hash = hash_signature(signature)
            architecture_index.add(signature_hash, signature, collection, parent_doc)
            item_signature_hashes.append(signature_hash)
            state.mark_parent_item_checked(parent_doc, signature_hash, architecture_index)
            save_state(args.state_file, state)

        summary = classify_collection(collection, item_signature_hashes, args)
        collection_summaries.append(summary)
        state.mark_collection_checked(collection, summary, architecture_index)
        save_state(args.state_file, state)

    result = build_result(args, collection_summaries, architecture_index)
    write_json(args.output_json, result)
    write_markdown(args.output_md, render_markdown_report(result))
```

## Notes For Future Implementation

- Prefer the Search API for bulk work.
- Avoid one full Item API call per object unless validation really requires it.
- Keep a public-only/default distinction clear in the report header.
- Include warnings prominently; architecture reports will otherwise look more definitive than the sampled data supports.
- Treat this as architecture discovery, not repository integrity validation.
- Review the output with BDR maintainers before turning common architectures into official ingest guidance.

## Addendum: Separate Architecture Identity From Observation Metadata

Follow-up review of `Understand_Project_and_`children_truncated`.md` raised an important naming and modeling issue.

The project goal is to discover common object architectures. In that context, a "signature" should ideally mean a stable identifier for a normalized object architecture. The current implementation includes `children_truncated` in the dictionary that gets hashed as `signature_hash`. That makes the current hash closer to an observation/check signature:

```text
architecture shape + scan completeness metadata
```

rather than a pure architecture signature:

```text
architecture shape only
```

`children_truncated` is valuable, but it describes the completeness of the observation, not the object architecture itself. It should remain visible in output and state so incomplete evidence is auditable, but it probably should not define architecture identity.

### Recommended Naming

Use names that make the distinction explicit:

- `architecture_signature`
  - normalized parent/child/datastream shape
  - intended to identify the architecture
- `architecture_signature_hash`
  - hash of `architecture_signature`
  - primary grouping key for common architectures
- `observation_metadata`
  - scan/check information, not architecture identity
  - examples: `children_truncated`, fetched child count, child `numFound`, `fetch_all_children`, sample strategy, row limits
- `observation_signature`
  - optional combined structure for audit/debugging
  - may include both `architecture_signature` and `observation_metadata`
- `observation_signature_hash`
  - optional hash of `observation_signature`
  - useful only if the implementation wants a separate key for "same architecture under same observation conditions"

Avoid using the bare name `signature_hash` in new output if two different signature concepts exist.

### Recommended Data Shape

For each sampled parent item, store something like:

```json
{
  "architecture_signature_hash": "abc123...",
  "architecture_signature": {
    "object_type": "implicit-set",
    "datastreams": ["MODS", "RELS-EXT", "rightsMetadata"],
    "child_count_bucket": "many:10+",
    "child_groups": [
      {
        "object_type": "image",
        "display_label": "",
        "datastreams": ["JP2", "MODS", "RELS-EXT", "rightsMetadata", "thumbnail"],
        "count_bucket": "many:10+"
      }
    ]
  },
  "observation_metadata": {
    "children_truncated": true,
    "fetched_child_count": 500,
    "child_num_found": 900,
    "fetch_all_children": false
  }
}
```

The architecture hash should be computed only from `architecture_signature`.

The observation metadata should be attached to item examples, collection summaries, and architecture candidates. It should be reported as warnings or caveats when any contributing item is truncated.

### Implementation Options

Option 1: Replace current grouping key with a pure architecture hash.

- Remove `children_truncated` from the hashed architecture structure.
- Keep `children_truncated` in per-item observation metadata.
- Group common architectures by `architecture_signature_hash`.
- Add candidate-level metrics:
  - `observed_item_count`
  - `truncated_observation_count`
  - `complete_observation_count`
  - `has_truncated_observations`
- This best matches the project goal.

Option 2: Keep both hashes during a transition.

- Continue writing the current `signature_hash` for backward compatibility, but rename or duplicate it as `observation_signature_hash`.
- Add new `architecture_signature_hash`.
- Use `architecture_signature_hash` for collection consistency and cross-collection architecture bucketing.
- Use `observation_signature_hash` only for debugging and audit trails.
- This is safest if existing output files or state files need a migration path.

Option 3: Keep truncated observations separate but linked.

- Use pure architecture identity for complete observations.
- For truncated observations, still compute `architecture_signature_hash`, but mark confidence as incomplete.
- Report incomplete observations under the same architecture candidate, with clear caveats.
- Do not let truncated observations alone establish that an architecture is fully known.

### Recommended Update

Implement Option 2 first, then eventually remove the ambiguous current `signature_hash` name.

Proposed near-term behavior:

1. Change `build_item_signature()` into two functions:
   - `build_architecture_signature(parent_doc, child_docs, args)`.
   - `build_observation_metadata(parent_doc, child_docs, child_num_found, children_truncated, args)`.
2. Hash only `architecture_signature` for `architecture_signature_hash`.
3. Store the hash in state as `parent_item_architecture_hashes`.
4. Update `ArchitectureIndex` to group by `architecture_signature_hash`.
5. Preserve truncation as candidate and example metadata:
   - candidate has `has_truncated_observations`.
   - candidate has `truncated_observation_count`.
   - example items include `children_truncated`.
6. Update JSON and Markdown report labels:
   - use `Architecture signature` for identity
   - use `Observation caveats` or `Observation metadata` for scan completeness
7. Keep a backward-compatibility note for old state files, because existing state keys such as `parent_item_signature_hashes` and `signature_hash` would no longer mean exactly the same thing.

### Why This Matters

If `children_truncated` stays inside the primary hash, the report can split one real architecture into two buckets:

- complete observation of architecture A
- truncated observation of architecture A

That protects against overclaiming, but it makes the hash less useful as the architecture identifier the project needs.

Separating architecture identity from observation metadata allows the report to say:

```text
These objects appear to share architecture A.
Some examples were observed completely.
Some examples were truncated and need caution or follow-up.
```

That better supports the goal of documenting common BDR object architectures while still preserving the uncertainty introduced by API limits and scan settings.
