# Plan: determine common BDR object architectures

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
--refresh-cache
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
    session: requests.Session
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

Use `requests.Session`.

Set an explicit user agent:

```text
BDRArchitectureSampler/0.1 (Brown University Library internal planning)
```

Use timeouts:

```python
timeout = (5, 60)
```

Retry only conservatively:

- retry `429`, `502`, `503`, `504`
- exponential backoff
- respect `Retry-After` if present
- do not retry `400`
- do not hammer through Cloudflare challenges

### Query encoding

Build params with `requests`, not hand-concatenated strings:

```python
params = {
    "q": 'rel_is_member_of_collection_ssim:"bdr:wum3gm43" AND -rel_is_part_of_ssim:*',
    "fl": "pid,primary_title,object_type,datastreams_ssi",
    "rows": 100,
    "start": 0,
}
session.get(f"{api_root}search/", params=params)
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
- write a resume file so long scans can continue without repeating requests

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
python determine_common_bdr_architectures.py \
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

    collections = discover_collections(client, args)
    for collection in collections:
        collection.top_level_item_count = count_top_level_items(client, collection.pid)

    selected = sorted(collections, key=lambda c: c.top_level_item_count, reverse=True)
    selected = selected[:args.max_collections]

    architecture_index = ArchitectureIndex()
    collection_summaries = []

    for collection in selected:
        parent_docs = fetch_sampled_top_level_items(client, collection.pid, args)
        item_signature_hashes = []

        for parent_doc in parent_docs:
            child_docs = fetch_children(client, parent_doc["pid"], args)
            signature = build_item_signature(parent_doc, child_docs, args)
            signature_hash = hash_signature(signature)
            architecture_index.add(signature_hash, signature, collection, parent_doc)
            item_signature_hashes.append(signature_hash)

        summary = classify_collection(collection, item_signature_hashes, args)
        collection_summaries.append(summary)

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
