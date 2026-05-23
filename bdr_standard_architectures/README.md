# bdr_standard_architectures

## Purpose

This project identifies common object architectures in the Brown Digital Repository (BDR).

It samples BDR collections, looks at top-level objects and their direct children, normalizes each object's object type and datastream inventory, and groups repeated parent/child patterns into architecture candidates.

The practical goal is to support future ingest planning: when an architecture is common in the BDR, it is more likely to be a pattern the repository already supports without custom development.

## Quick Start

Show all CLI options:

```bash
uv run ./main.py --help
```

Small public-API smoke run:

```bash
uv run ./main.py \
  --max-collections 1 \
  --max-items-per-collection 5 \
  --rows 5 \
  --sleep-seconds 1 \
  --output-json /tmp/bdr_architectures.json \
  --output-md /tmp/bdr_architectures.md
```

Default run:

```bash
uv run ./main.py
```

The default run writes:

- `../bdr_standard_architectures_output/common_architectures.json`
- `../bdr_standard_architectures_output/common_architectures.md`
- `../bdr_standard_architectures_output/architecture_cache/run_state.json`
- cached API responses in `../bdr_standard_architectures_output/architecture_cache/`

The defaults are resolved as paths in a sibling directory of this project root, not inside the directory that contains `.git/`.

## Expanded Default Command

The minimal command:

```bash
uv run ./main.py
```

is equivalent to the following value-taking arguments:

```bash
uv run ./main.py \
  --api-root https://repository.library.brown.edu/api/ \
  --max-collections 20 \
  --max-items-per-collection 100 \
  --rows 100 \
  --sleep-seconds 0.25 \
  --output-json ../bdr_standard_architectures_output/common_architectures.json \
  --output-md ../bdr_standard_architectures_output/common_architectures.md \
  --cache-dir ../bdr_standard_architectures_output/architecture_cache \
  --state-file ../bdr_standard_architectures_output/architecture_cache/run_state.json \
  --full-item-validation-sample 0 \
  --collection-query-mode public-top-level \
  --collection-pids "" \
  --skip-collections "" \
  --min-consistency-percent 90.0 \
  --top-architectures 25 \
  --sample-strategy first \
  --random-seed 0 \
  --min-sample-size 10
```

The boolean flags are false when omitted. The default run does not set:

- `--refresh-cache`
- `--refresh-state`
- `--no-resume`
- `--include-private`
- `--include-singletons`
- `--include-mime-types`
- `--fetch-all-children`

This section is intentionally separate from Quick Start so the normal usage stays easy to scan.

## Follow-Up Scans

The default run scans the largest 20 selected collections because `--max-collections` defaults to `20`.

At the moment, the script cannot append "the next 10 collections" to the same completed default run state by simply changing `--max-collections` from `20` to `30`. The state file validates material parameters before resuming, and `max_collections` is one of those material parameters. That means a second run with `--max-collections 30` and the same state file will stop with a state-compatibility error unless you reset or separate the state.

To produce a 30-collection report, run a new analysis:

```bash
uv run ./main.py \
  --max-collections 30 \
  --refresh-state
```

That reruns the analysis state from scratch, but it can still reuse cached API responses unless `--refresh-cache` is also set.

To inspect 10 known additional collections separately, use explicit collection PIDs and separate output/state files:

```bash
uv run ./main.py \
  --collection-pids bdr:example1,bdr:example2,bdr:example3 \
  --output-json ../bdr_standard_architectures_output/additional_architectures.json \
  --output-md ../bdr_standard_architectures_output/additional_architectures.md \
  --state-file ../bdr_standard_architectures_output/architecture_cache/additional_run_state.json
```

That does not merge the new scan into the original report; it creates a separate targeted report.

## Program Flow

### 1. Parse CLI Arguments

`main.py` parses arguments in `parse_args()`.

What it does:

- Defines the API root, scan limits, output paths, cache/state behavior, sampling strategy, and report filters.
- Passes the parsed arguments into `lib.sampler.run_sampler()`.

Why that is useful:

- The sampler has many controls, but they all map to one of a few concerns: API-friendly request behavior, scan scope, sampling quality, resumability, architecture identity, or output filtering.

### 2. Create API Client, Cache, And State

`lib.sampler.run_sampler()` creates:

- `lib.cache.Cache`
- `lib.api.ApiClient`
- a resumable state object from `lib.state.load_or_initialize_state()`

What it does:

- Uses `httpx` with explicit timeouts.
- Sends a BDR-specific user agent.
- Sleeps between API requests.
- Caches API JSON responses by request path, params, API root, and script version.
- Loads compatible run state when available.

Why that is useful:

- The public BDR API should be treated gently.
- Cached responses avoid repeating the same API work during development.
- State lets a long scan resume after a network failure or manual stop without losing completed analysis.

### 3. Discover Collections

`lib.collections.discover_collections()` decides which collections are candidates.

What it does:

- Uses explicit `--collection-pids` when provided.
- Otherwise uses the Collection API endpoint by default.
- Falls back to Search API discovery if needed.
- Applies `--skip-collections`.

Why that is useful:

- Explicit collection lists are useful for targeted investigation.
- Automatic discovery is useful for repository-wide pattern finding.
- Skipping known unusual collections keeps the common-architecture report focused.

### 4. Count Top-Level Items

`lib.collections.count_top_level_items()` counts public top-level, non-collection items per collection.

What it does:

- Searches for records that are members of the collection.
- Excludes child objects with `-rel_is_part_of_ssim:*`.
- Excludes subcollections with `-object_type:bdr-collection`.
- Saves completed collection counts into the state file.

Why that is useful:

- Sorting collections by top-level item count lets the script inspect the largest collections first.
- Excluding children keeps collection size tied to object architectures rather than page counts.
- Saving count progress avoids repeating many count queries after interruption.

### 5. Select Collections

`lib.collections.select_collections()` sorts candidate collections by top-level item count and keeps the largest `--max-collections`.

What it does:

- Produces the selected collection list for the scan.
- Saves that list in run state.

Why that is useful:

- Common architectures may be most likely to appear in large collections.
- Saving the selected list makes resumed runs deterministic.

### 6. Sample Top-Level Items

`lib.sampling.fetch_sampled_top_level_items()` fetches parent objects for each selected collection.

What it does:

- Uses `--sample-strategy` to choose `first`, `evenly-spaced`, or `random`; the default is `first`.
- Limits per-collection parent sampling with `--max-items-per-collection`.
- Limits page size with `--rows`.
- Requests only fields needed for architecture detection.

Why that is useful:

- Sampling avoids scanning every item in large collections.
- Field-limited Search API requests are cheaper than full Item API calls.
- Different sampling strategies trade speed, determinism, and representativeness.

### 7. Fetch Direct Children

`lib.sampling.fetch_children()` fetches child objects for each sampled parent.

What it does:

- Searches for `rel_is_part_of_ssim:"<parent-pid>"`.
- Retrieves child object type, datastreams, pagination, relationship hints, and display label.
- Sorts paginated children naturally before unordered children.
- Marks children as truncated if a parent has more than one page of children and `--fetch-all-children` is not set.

Why that is useful:

- Parent/child shape is central to BDR object architecture.
- Natural child sorting makes page-like objects behave consistently.
- Truncation prevents the report from presenting incomplete child data as complete.

### 8. Build Architecture Signatures

`lib.signatures.build_item_signature()` normalizes one sampled parent and its children.

What it does:

- Records parent object type.
- Parses parent `datastreams_ssi`.
- Groups children by object type, display label, and datastream set.
- Uses child count buckets: `none`, `one`, `few:2-9`, `many:10+`.
- Hashes the deterministic signature JSON into a short signature hash.

Why that is useful:

- Signatures ignore unstable values like PIDs and titles.
- Count buckets keep a 20-page and 200-page book-like object in the same architecture family.
- Hashes make repeated architecture patterns easy to count and compare.

### 9. Accumulate Candidates And Checkpoint Progress

`lib.models.ArchitectureIndex` tracks architecture candidates, examples, and collection counts.

What it does:

- Adds each sampled item to a signature bucket.
- Stores representative example items and collections.
- Saves checked parent items using a collection PID plus parent PID key.
- Saves populated architecture candidates in the state file.

Why that is useful:

- The examples make the final report auditable.
- The collection-plus-parent checked key handles objects that belong to multiple collections.
- Persisting candidates means a resumed scan can continue from the last completed unit of work.

### 10. Classify Collections

`lib.classification.classify_collection()` summarizes each collection after its sample is processed.

What it does:

- Counts signatures in the sampled items.
- Finds the dominant signature.
- Computes the dominant percentage.
- Classifies the collection as `uniform`, `mostly_uniform`, `mixed`, or `insufficient_sample`.

Why that is useful:

- A collection can have one clear architecture, a mostly consistent architecture with exceptions, or intentionally mixed content.
- Classifying collections avoids hiding variation behind a single aggregate architecture count.

### 11. Write Reports

`lib.report.build_result()` builds JSON output, and `lib.report.render_markdown_report()` builds Markdown output.

What it does:

- Sorts architecture candidates by dominance and sampled item count.
- Applies report filters such as `--top-architectures` and `--include-singletons`.
- Writes machine-readable JSON and human-readable Markdown.

Why that is useful:

- JSON supports downstream processing.
- Markdown supports human review with BDR maintainers and ingest planners.

## Argument Reference

### API And Safety

#### `--api-root`

Default: `https://repository.library.brown.edu/api/`

What it does:

- Sets the BDR API root used for collection and search requests.

Why that is useful:

- Public scans can use the default.
- Internal or staging scans can point at a different API root without code changes.

#### `--sleep-seconds`

Default: `0.25`

What it does:

- Waits this many seconds before each uncached API request.

Why that is useful:

- Keeps the script gentle toward the public API and reduces the chance of triggering Cloudflare or rate-limit behavior.

#### `--rows`

Default: `100`

What it does:

- Sets the Search API page size for top-level item sampling.
- The code clamps this to the public Search API maximum of `500`.

Why that is useful:

- Smaller pages are gentler and easier to debug.
- Larger pages reduce request count when scanning more data.

### Output Files

#### `--output-json`

Default: `../bdr_standard_architectures_output/common_architectures.json`

What it does:

- Sets the final machine-readable JSON report path.

Why that is useful:

- JSON is useful for scripts, diffing repeated runs, and preserving complete report data.

#### `--output-md`

Default: `../bdr_standard_architectures_output/common_architectures.md`

What it does:

- Sets the final Markdown report path.

Why that is useful:

- Markdown is easier for people to review, share, and turn into ingest guidance.

### Cache And Resume State

#### `--cache-dir`

Default: `../bdr_standard_architectures_output/architecture_cache`

What it does:

- Sets where cached API JSON responses are stored.

Why that is useful:

- Cached API responses reduce repeated network requests during development and make reruns more deterministic.

#### `--state-file`

Default: `../bdr_standard_architectures_output/architecture_cache/run_state.json`

What it does:

- Sets where resumable scan progress is stored.

Why that is useful:

- If the network fails or the script is interrupted, a later run can skip completed counts, collections, and sampled parent items.

#### `--refresh-cache`

Default: false

What it does:

- Ignores existing cached API responses and writes fresh cache entries.

Why that is useful:

- Use this when API data may have changed and you want fresh responses.
- It does not automatically discard run state.

#### `--refresh-state`

Default: false

What it does:

- Starts with new resumable state even if `--state-file` already exists.

Why that is useful:

- Use this when changing scan parameters intentionally or when previous progress should not be reused.

#### `--no-resume`

Default: false

What it does:

- Disables state-file resume behavior for the run.

Why that is useful:

- Useful for one-off tests where you do not want progress written or reused.

### Collection Scope

#### `--max-collections`

Default: `20`

What it does:

- Limits how many selected collections are scanned after sorting by top-level item count.

Why that is useful:

- Keeps default scans bounded while still focusing on large collections likely to reveal common patterns.

#### `--collection-query-mode`

Default: `public-top-level`

Choices: `public-top-level`, `search`

What it does:

- Chooses how collections are discovered when `--collection-pids` is not provided.
- `public-top-level` tries the Collection API endpoint first, then falls back to Search API discovery.
- `search` uses Search API collection discovery directly.

Why that is useful:

- The Collection API is the preferred public route.
- Search mode is useful if the collection endpoint does not expose enough collection records for a run.

#### `--collection-pids`

Default: empty

What it does:

- Accepts a comma-separated list of collection PIDs to scan.
- Bypasses automatic collection discovery.

Why that is useful:

- Useful for targeted analysis of known collections.
- Also useful for repeatable debugging with a small fixed input set.

#### `--skip-collections`

Default: empty

What it does:

- Accepts a comma-separated list of collection PIDs to exclude from automatic or explicit collection lists.

Why that is useful:

- Lets you avoid known special-purpose, pathological, or out-of-scope collections without changing code.

#### `--include-private`

Default: false

What it does:

- Records the caller's intent to include private content in material parameters.
- The current implementation does not add authentication or privileged access by itself.

Why that is useful:

- Keeps public/default and internal/private scan intent explicit in state compatibility and report parameters.
- If an internal API root or future auth support is added, this flag is already part of the scan contract.

### Item Sampling

#### `--max-items-per-collection`

Default: `100`

What it does:

- Limits how many top-level parent items are sampled from each selected collection.

Why that is useful:

- Bounds scan cost while still allowing enough examples to detect dominant architectures.

#### `--sample-strategy`

Default: `first`

Choices: `first`, `evenly-spaced`, `random`

What it does:

- `first`: samples the first N items by stable PID sort.
- `evenly-spaced`: samples offsets across the whole collection.
- `random`: samples random offsets using `--random-seed`.

Why that is useful:

- `first` is fast and deterministic.
- `evenly-spaced` reduces bias when collections changed over time.
- `random` can be useful for exploratory spot checks while remaining reproducible with a seed.

#### `--random-seed`

Default: `0`

What it does:

- Sets the seed used by `--sample-strategy random`.

Why that is useful:

- Makes random sampling reproducible.

### Child Fetching And Signature Detail

#### `--fetch-all-children`

Default: false

What it does:

- Fetches all child pages when a sampled parent has more than 500 direct children.
- Without it, the script records the signature as truncated.

Why that is useful:

- Default truncation is safer and cheaper for very large objects.
- Fetching all children is useful when exact child-group composition matters for a smaller targeted scan.

#### `--include-mime-types`

Default: false

What it does:

- Includes MIME type in datastream tokens when available, for example `JP2:image/jp2`.

Why that is useful:

- Leaving MIME types out groups objects by datastream ID, which is usually the architecture-level concern.
- Including MIME types is useful for diagnosing variation inside otherwise similar architectures.

### Collection Classification

#### `--min-consistency-percent`

Default: `90.0`

What it does:

- Sets the threshold for classifying a collection as `mostly_uniform`.

Why that is useful:

- Allows a collection with a few exceptions to still be recognized as having a dominant architecture.

#### `--min-sample-size`

Default: `10`

What it does:

- Sets the minimum number of sampled top-level items needed before a collection can be classified as uniform, mostly uniform, or mixed.
- This is only a confidence floor for classification; it does not cap how many sampled items are used. If 100 parent objects are sampled, all 100 are used.

Why that is useful:

- Prevents tiny samples from looking more conclusive than they are.

### Report Filtering

#### `--top-architectures`

Default: `25`

What it does:

- Limits how many architecture candidates appear in the final report.

Why that is useful:

- Keeps the Markdown report focused on the most common patterns.

#### `--include-singletons`

Default: false

What it does:

- Includes architectures seen only once in the final architecture list.

Why that is useful:

- The default hides one-off architectures so the report emphasizes common patterns.
- Including singletons is useful for diagnostics or for reviewing outliers.

#### `--full-item-validation-sample`

Default: `0`

What it does:

- Reserved parameter for future full Item API validation sampling.
- It is stored in material parameters and state compatibility checks, but the current implementation does not perform full Item API validation.

Why that is useful:

- Keeps room for a later validation mode without changing the run-state contract.

## Outputs

### JSON Report

The JSON report contains:

- run timestamp
- API root
- material parameters
- collection summaries
- architecture candidates
- warnings

Use this when you need complete structured data.

### Markdown Report

The Markdown report contains:

- summary counts
- most common architecture sections
- representative collections and items
- collections with mixed architectures

Use this for human review and documentation drafting.

### State File

The state file contains:

- discovered collections
- selected collections
- checked collection counts
- checked collections
- checked parent items
- parent item signature hashes
- populated architecture candidates
- collection summaries

Use this to resume interrupted scans. The script validates state compatibility against the current API root, script version, and material parameters before resuming.

### Cache Files

The cache directory stores API responses keyed by request path and params.

Use this to avoid repeating identical API requests during development. Cache files are not the same as run state: cache stores HTTP responses, while state stores analysis progress.

## Reading The Code

The main code paths are:

- `main.py`: CLI parsing and final output writes.
- `lib/sampler.py`: top-level orchestration.
- `lib/api.py`: API access, retries, and rate limiting.
- `lib/cache.py`: response cache.
- `lib/state.py`: resumable state.
- `lib/collections.py`: collection discovery and counting.
- `lib/sampling.py`: top-level item and child fetching.
- `lib/signatures.py`: architecture signature construction.
- `lib/classification.py`: collection consistency classification.
- `lib/models.py`: collection and architecture index models.
- `lib/report.py`: JSON result assembly and Markdown rendering.
- `lib/utils.py`: small shared helpers.
