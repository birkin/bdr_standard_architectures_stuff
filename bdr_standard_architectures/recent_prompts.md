## original prompt

Goal: develop a plan for a script.

Context:

The idea from a readme...

```
## Purpose

The purpose of this script is to identify the most common standard object-architectures used in the Brown Digital Repository (BDR).

The reason for this is so we can document and share with future ingesters the standard architectures that we know work and are supported without custom development.

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
```

- I'm thinking it'd be worth reviewing:
	- `bdr_ecosystem_project/AGENT_info/bdr_apis_project__AGENT_INDEX.yaml`
	- `bdr_ecosystem_project/AGENT_info/bdr_solr_conf__AGENT_INDEX.yaml`
	- <https://github.com/Brown-University-Library/bdr_api_documentation/wiki>

Tasks:

- Review the above recommendations.

- Review any other file you think would be useful.

- Save a thorough plan for such a script to `bdr_ecosystem_project/misc/PLAN__determine_most_common_architectures.md`

---

## followup prompts

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
