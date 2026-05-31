# Extras

Small helper scripts for working with generated BDR architecture outputs.

## Convert Object-Definition Signatures To TSV

Script:

```bash
cd bdr_object_architectures
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

The `specifications/` input directory and `TSVs/` output directory are siblings of `bdr_object_architectures/`, not inside the project package.

## Get One Object-Definition Signature

Script:

```bash
cd bdr_object_architectures
uv run './extras/get_object_definition_signature.py' bdr:123456
```

The script fetches one BDR item from the Search API and prints the object-definition signature entry as JSON. It uses the same object-definition signature builder as the main sampler, but it does not run collection sampling or write specification YAML.

To compare the generated hash with the sibling specification file:

```bash
uv run './extras/get_object_definition_signature.py' bdr:123456 --compare-specifications
```

The comparison reads:

```text
../specifications/object_definition_signatures.yaml
```

If that file is not present, the JSON output includes a `specification_match.message` noting that the comparison file could not be found at the displayed relative path.

To also save the JSON output:

```bash
uv run './extras/get_object_definition_signature.py' bdr:123456 --output-json ../TSVs/object_definition_signature_bdr_123456.json
```
