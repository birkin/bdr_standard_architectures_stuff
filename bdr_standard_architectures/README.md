# bdr_standard_architectures


## Purpose

The purpose of this script is to identify the most common standard object-architectures used in the Brown Digital Repository (BDR).

The reason for this is so we can document and share with future ingesters the standard architectures that we know work and are supported without custom development.


## Plan

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


## Usage

```bash
uv run ./main.py
```

---
