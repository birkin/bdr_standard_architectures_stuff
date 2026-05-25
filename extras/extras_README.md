# Extras

Small helper scripts for working with generated BDR architecture outputs.

## Convert Object-Definition Signatures To TSV

Script:

```bash
cd bdr_standard_architectures
uv run './extras/convert_object_definition_signatures_to_tsv.py'
```

Input:

```text
../specifications/object_definition_signatures.yaml
```

Output:

```text
../TSVs/object_definition_signatures.tsv
```

The TSV contains one row per object-definition signature entry. Columns include signature hash, label, description, exemplar PIDs, object type, `typeOfResource`, parent/child/order booleans, datastream IDs, datastream detail JSON, and full signature JSON.

The `specifications/` input directory and `TSVs/` output directory are siblings of `bdr_standard_architectures/`, not inside the project package.
