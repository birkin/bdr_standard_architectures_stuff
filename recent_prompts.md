_(in chronological order)_

---

- Review `AGENTS.md` for coding-directives.

- Review `bdr_standard_architectures/PLAN__determine_most_common_architectures.md`

- You're already being nice to the server in the plan; thanks.

- I may have missed this in the plan -- but if it's not there, save some state of:
	- populated common-architecture-candidates 
	- what has been checked

	...so that if there's a network failure, the script can pick up where it left off
	
- Add these to the plan at `bdr_standard_architectures/PLAN__determine_most_common_architectures.md`

---

Put most helper files in `bdr_standard_architectures/lib/` and import them as necessary.

Keep only `main()` -- and the code it _directly_ calls in `bdr_standard_architectures/main.py`.

---

Goal: Document program flow and arguments.

Context:

- There are a large number of possible arguments that can be sent to `bdr_standard_architectures/main.py` main().

- That can be overwhelming if not understood.

Tasks:

- Review the `bdr_standard_architectures/` code.

- Update `bdr_standard_architectures/README.md` to document:
	-  the flow of code
	-  the purpose of each argument
	-  this readme documentation should include both the concept of "what it does" and "why that's useful".

---

- Re the line: """- Uses `--sample-strategy` to choose `first`, `evenly-spaced`, or `random`."""

  I'm thinking that for some of these arguments, there is a default. If so, indicate in the appropriate argument section what the default is, if it's not already there.

  Add this prompt to `bdr_standard_architectures/recent_prompts.md`.

---

- Ensure all default output paths are _not_ in the project-root (where the .git/ directory lives). Set all default output paths to the sibling directory of the project-root.

  Add this prompt to `bdr_standard_architectures/recent_prompts.md`.

---

questions: 

- if I just run the script in the most minimal way, what would be the equivalent all-argument command? (Add that to an appropriate place in the documentation -- but not in a place where it confuses easy Usage instructions).

- if I run the script in the most minimal way, and it goes through X collections (I think the default is 20, yes?). If I then want to check an _additional_, say, 10 collections, what would the follow up command be -- _if_ it's even possible to "build on" previous work. (If it's not, that's ok -- I'm not asking you to add that functionality if it's not there.)

- Add this prompt to `bdr_standard_architectures/recent_prompts.md`.

---

After the `Expanded Default Command` section, and an `Installation` section.

Have it include:
- assumption that `uv` is installed, with a link to the atral-uv-installation web-page.
- cd-ing to a `stuff` directory
- running the git-clone command
- running uv sync

...and then referring folk to the "Usage" section above.

(I may have left stuff out)

- Add this prompt to `bdr_standard_architectures/recent_prompts.md`.

---

Goal: Explore options for saving a signature that reflects the object-architecture.

Context:

- Since the goal of this is to gather data to establish common object-architectures. I had thought the "signature" was a unique identifier for a unique object-architecture.

- However, review `bdr_standard_architectures/Understand_Project_and_`children_truncated`.md`

Goal: 

- propose ways the code could be updated to have a signature that reflects the object-architecture.

- it's ok if it's an additional signature, as long as the names are clear.

- Add your thoughts for a possible update to an addendum to `bdr_standard_architectures/PLAN__determine_most_common_architectures.md`

- Add this prompt to `bdr_standard_architectures/recent_prompts.md`.

---

Goal: Rethink object-architecture signatures, and make a new plan-document.

Context:

- object-architecture signature logic can be based on parent-child relationship, the parent-object's datastreams, and aspects of the child-objects.

- I'm thinking of a new approach:
	- There is a signature representing the parent-object relationship
	- There is a signature representing on object's datastreams
	- There is a signature representing an item's visibility. This may be for a future implementation since we're only using the public BDR-APIs.
	- What else might be reasonable for a specific-level signature?
	- Finally, there could be an overall calculated object-architecture signature that is based on the individual signatures.

- I'm thinking that the way to build this out might be to update code to calculate these signatures on individual or a small set of collections.

- "yaml" files in a directory called "specifications/" could incorporate human-readable "description" as well as the signature.

- eventually the type and especially number of different types of signatures might warrant the yaml files being stored in subdirectories of the "specifications/" directory -- but initially let's try to either use a single yaml file or multiple yaml files all within the "specifications/" directory.

Tasks:

- Think about this idea.

- Come up with one or two proposals to structure the file or files for this more-specific specification-approach.

- Do not think about coding implementation yet -- let's explore the ideas.

- Save the plan to `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md`

Main response:

- Created `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md`.
- Proposed a dimension-signature model separating parent relationship, object datastream, child profile, future visibility, presentation/navigation, and auxiliary relationship signatures.
- Included two YAML organization proposals: a single registry file and multiple flat files in `specifications/`.
- Recommended starting with multiple flat YAML files if the project is moving toward reusable specifications, while noting that a single registry file may be better for short-lived brainstorming.

---

Goal: Refine `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md` plan.

Context:

- Review `bdr_standard_architectures/README.md` to understand the purpose of the project. Ignore the current specific implementation.
- Incorporate follow-up decisions about parent relationship signatures, object datastream signatures, open-access signatures, visibility signatures, auxiliary relationship signatures, future video-streaming questions, and future allowed-values YAML files.
- Incorporate direct `FEEDBACK` entries from the plan and remove those raw feedback entries from the final document.

Main response:

- Updated `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md`.
- Added README-derived project context emphasizing observed BDR behavior and ingest-planning usefulness.
- Clarified initial fields for `parent_relationship_signatures.yaml` and `object_datastream_signatures.yaml`.
- Added `open_access_signatures.yaml` and `auxiliary_relationships_signatures.yaml` to the plan and YAML examples.
- Added an `Answered Questions` section converting prior open questions and inline feedback into decisions.
- Added future open questions about video streaming, allowed-values YAML files, required/optional datastream interpretation, and unknown embargo status.
- Verified that no `FEEDBACK` markers remain.

---

also update the plan to go with `## Proposal 2: Multiple Flat YAML Files In `specifications/`

My context answers should have made that clear.

Please remove those two options and their strenghts and weaknesses -- since this has been decided. thx.

Main response:

- Updated `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md` to remove the proposal comparison.
- Replaced the proposal sections with a single decided `Specification File Structure` section.
- Removed strengths, weaknesses, recommendation, and remaining Proposal 1 / Proposal 2 language.
- Updated the proposed next step to refer only to multiple flat YAML files.

---

Plan feedback:

- remove "object_type" from the parent-child relationship section.

- rename `object_datastream_signatures.yaml` to something like `object_definition_signatures.yaml` because I'd like to include `object_type` and also `typeOfResource` when available.

Main response:

- Updated `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md`.
- Removed `parent_object_type` from the parent relationship signature section.
- Renamed the object datastream signature concept/file to `object_definition_signatures.yaml`.
- Added `typeOfResource` as an object definition field when available.
- Updated YAML examples and composite signature references to use object-definition terminology.
- Verified that no stale `object_datastream`, `parent_object_type`, or `parent_datastream_signature` references remain.

---

Plan feedback:

- remove `### 3. Child Profile Signature` , and any references -- we'll not currently focus on the children as a group.

Main response:

- Updated `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md`.
- Removed the `Child Profile Signature` section.
- Removed `child_profile_signatures.yaml` from the specification file list.
- Removed child-profile references from YAML examples, composite signatures, initial signature lists, and answered questions.
- Verified no child-profile references remain.

---

Plan feedback:

- Add to `### 2. Object Definition Signature`:
	- 'has_parent', 'has_children', 'is_ordered'

- Remove `### 5. Presentation Or Navigation Signature` for now -- i'm hoping streaming can be detected other ways.

Main response:

- Updated `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md`.
- Added `has_parent`, `has_children`, and `is_ordered` to Object Definition Signature.
- Updated object-definition YAML examples with the new fields.
- Removed the Presentation Or Navigation Signature section.
- Updated the video-streaming open question to avoid presentation/navigation terminology.
- Verified no presentation/navigation terms remain.

---

Plan feedback:

- Provide an example yaml-file for each of these:
	- `specifications/parent_relationship_signatures.yaml`
	- `specifications/object_definition_signatures.yaml`
	- `specifications/open_access_signatures.yaml`
	- `specifications/visibility_signatures.yaml`
	- `specifications/auxiliary_relationships_signatures.yaml`
	- `specifications/composite_architecture_signatures.yaml`
- Add hash-based identifier signatures to each individual signature file.
- Add a placeholder for three BDR PIDs that can be exemplars.
- Note that composite signatures may be hashes of component hashes with human descriptive narrative.

Main response:

- Updated `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md`.
- Added YAML examples for all six decided specification files.
- Added `signature_hash` placeholders to individual and composite signature examples.
- Added `exemplar_pids` placeholders with three BDR PID slots per signature.
- Added composite signature examples using component signature IDs and component `signature_hash` values.
- Added guidance that composite hashes can be calculated from component hashes while descriptions, narratives, and exemplars support human review.

---

Plan feedback:

- For the `# specifications/composite_architecture_signatures.yaml` example yaml file: the actual `signature` content used to build the `signature_hash` should not include the human-readable "label". That could change. Do keep the labels for each component -- just don't have them be part of the content-to-be-hashed.

Main response:

- Updated `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md`.
- Moved human-readable component labels in the composite YAML example into `component_labels`.
- Left only component `signature_hash` values inside the composite `signature` block.
- Clarified that `description`, `narrative`, `component_labels`, and `exemplar_pids` support review but should not normally affect the composite hash.

---

Goal: Develop a thorough implementation plan.

Context:

- Removed next-steps sections from `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md`.
- Review `README.md`, `PLAN__consider_specific_signatures.md`, and `AGENTS.md`.
- Preserve as much existing flag behavior and API response caching as reasonably possible.
- Focus new work on capturing and building out signatures.
- Keep default sampling of 100 parent items per collection.
- Add default examination of 100 child objects per parent item.
- Default to one request every 2 seconds due to increased child-object inspection.
- Save the implementation plan to `bdr_standard_architectures/plans/PLAN__implement_specific_signatures.md`.
- Do not change code yet.

Main response:

- Created `bdr_standard_architectures/plans/PLAN__implement_specific_signatures.md`.
- Included current project context, implementation architecture, target signature model, child-object sampling changes, API/load concerns, state/cache compatibility, module-by-module changes, testing plan, smoke commands, risks, and open implementation decisions.
- Did not change runtime code.

---

Prompt:

Here is a prompt that created a new plan:

[--- START ---]
Goal: Develop a thorough implementation plan.

Context:

- I removed the next-steps sections from the `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md` -- there will be a new plan for implementation.
- Review `bdr_standard_architectures/README.md` to get an idea of the overall goal of this project -- and of the _current_ soon-to-be-changed implementation.
- Review the `bdr_standard_architectures/plans/PLAN__consider_specific_signatures.md` -- this will be the basis for the new plan.
- Review `bdr_standard_architectures/AGENTS.md` for coding-directives.
- I really like the multiple flags and the caching of api responses in the current code implementation. Leave as much of the existing functionality in-place as reasonably possible.
- The focus of the new work is on capturing and building out signatures.
- Keep the idea that for a given collection -- default to examining 100 parent-items.
- Add to this the idea that for each parent item -- default to examining 100 child-objects.

Tasks:

- Create an implementation plan to update the code to implement the new specification architecture.
- Due to examining more child-objects, there may be more server load, so default to one request every 2 seconds.
- Add to the plan any contextual info that might be useful if the plan were to be implemented in a new session.
- Save the new plan to `bdr_standard_architectures/plans/PLAN__implement_specific_signatures.md`.
- Don't change any code yet -- this is plan-work.
[--- END ---]

...And here is the resulting plan: `bdr_standard_architectures/plans/PLAN__implement_specific_signatures.md`.

Please review the prompt, and the plan, and make any edits to the plan that would be useful for you to implement. Also feel free to add a section to the plan of Questions/Decision-points for me to answer.

Main response:

Reviewed the source prompt, existing implementation plan, `PLAN__consider_specific_signatures.md`, `README.md`, `AGENTS.md`, and relevant current modules. Updated `plans/PLAN__implement_specific_signatures.md` with implementation-focused clarifications around child sampling metadata, signature identity boundaries, child object profile structure, concrete state keys, report output names, test targets, and a Questions / Decision Points section for Birkin.

---

Prompt:

add table-of-contents/index links near the top of `bdr_standard_architectures/plans/PLAN__implement_specific_signatures.md` for top-level headings only.

Main response:

Added a top-level-only table of contents near the top of `bdr_standard_architectures/plans/PLAN__implement_specific_signatures.md`.

---

Prompt:

I've updated the plan with "FEEDBACK" (all caps), and look at the last few commits in case there were some direct-changes without that label.

Update the plan accordingly, and do feel free to keep a section for new questions if desired.

Main response:

Updated `bdr_standard_architectures/plans/PLAN__implement_specific_signatures.md` to incorporate the marked feedback and recent direct plan changes. Added `children_signatures.yaml`, made specification YAML generation a core normal output, added the 1,000-child safety cap for `--fetch-all-children`, resolved known Solr/API field names, made MIME details part of object-definition identity by default, removed stale opt-in/feedback question language, and kept a short open-decisions section for implementation-time choices.

---

Prompt:

- I've updated the plan with "FEEDBACK" (all caps). Update the plan accordingly.

- rename `fetch-all-children` to something like `fetch-all-children-max-1000` to clarify the behavior

Main response:

Updated `bdr_standard_architectures/plans/PLAN__implement_specific_signatures.md` to incorporate the marked feedback. Renamed the child-fetch flag to `--fetch-all-children-max-1000`, removed the planned `--include-mime-types` flag, reframed field access as BDR API / BDR Search API access, required structural validation tests for generated YAML if no schema validator is used, and clarified YAML merge preservation for label-like human-entered fields.

---

Prompt:

- Review `bdr_standard_architectures/AGENTS.md` for coding-directives.

- Review `bdr_standard_architectures/plans/PLAN__implement_specific_signatures.md` for the plan to implement.

- Proceed with implementation!

Thx!

Main response:

Implemented the specific signature architecture. Added child sampling limits and `--fetch-all-children-max-1000`, removed `--include-mime-types`, added dimension/composite signature bundles, updated resumable state and reports, added YAML specification generation with merge behavior, added PyYAML, updated README and tests, and verified with `uv run ./run_tests.py`, `uv run ruff check .`, and `uv run ./main.py --help`.

---

Prompt:

update the code so that new specifications found are saved after each collection.

Main response:

Updated the sampler so specification YAML files are written after each completed collection, immediately after collection state is saved, while keeping the final specification write at the end of the run. Updated README documentation and verified with `uv run ./run_tests.py` and `uv run ruff check .`.

---

Prompt:

create a script that will save each `bdr_standard_architectures/specifications/object_definition_signatures.yaml` entry to a TSV file, saved to `TSVs/object_definition_signatures.tsv`. Save the script to `bdr_standard_architectures/extras/convert_ object_definition_signatures_to_tsv.py`

Main response:

Added `extras/convert_ object_definition_signatures_to_tsv.py`, which reads `specifications/object_definition_signatures.yaml` and writes `TSVs/object_definition_signatures.tsv` with one row per signature entry. Ran the script successfully and verified it wrote 43 data rows. Ran `uv run ruff check './extras/convert_ object_definition_signatures_to_tsv.py'`.

---

Prompt:

add an `bdr_standard_architectures/extras/extras_README.md` file with usage instructions.

Main response:

Added `extras/extras_README.md` with usage instructions for `convert_ object_definition_signatures_to_tsv.py`, including the command, input path, output path, and TSV column summary.

---

Prompt:

create the TSVs folder in the project-repo _parent_ directory.

Main response:

Created `TSVs/` in the project repository parent directory.

---

Prompt:

update the script to save the TSV files to a TSV directory sibling to (not inside) of `bdr_standard_architectures`.

Main response:

Updated `extras/convert_object_definition_signatures_to_tsv.py` to write to the parent-level `../TSVs/object_definition_signatures.tsv`, updated `extras/extras_README.md`, ran the converter successfully, and verified ruff passed.

---

Prompt:

Goal: Update the way mime-type check is handled.

Context:

- Too much of the mime-type info is just "noise".
- There are a "default" or "standard" set of datastreams for which the mime-type is always the same, so I'd like to exclude those. These are:
  - DC
  - MODS
  - RELS-EXT
  - RELS-INT
  - irMetadata
  - rightsMetadata
  - thumbnail

Tasks:

- Review `bdr_standard_architectures/AGENTS.md` for coding-directives.
- Update the code so that mime-type handling does not include the default/standard data-streams in it's signature calculations.
- Update any necessary documentation

Thx.

Main response:

Updated MIME handling so standard datastream IDs remain in `datastream_ids` but their MIME types are excluded from object-definition signature identity. Bumped the signature architecture version, updated README documentation, added tests for standard datastream MIME exclusion, and verified with `uv run ./run_tests.py` and `uv run ruff check .`.

---
