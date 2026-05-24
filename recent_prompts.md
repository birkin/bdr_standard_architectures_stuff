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
