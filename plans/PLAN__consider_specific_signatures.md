# Plan: consider more-specific object-architecture signatures

## Purpose

Rethink object-architecture signatures as a set of smaller, named, human-readable specification dimensions that can be composed into an overall object-architecture signature.

The current architecture-signature idea groups an observed parent object, its datastreams, and its children into one normalized structure. That is useful for finding common architectures, but it may be too coarse for explaining *why* two architectures match or differ.

A more-specific signature approach would separate architectural evidence into dimensions such as relationship shape, datastream inventory, child-object profile, and possibly visibility. Each dimension can have its own named signature and description. A calculated overall signature can then be derived from the combination of dimension signatures.

## Working Idea

Use YAML specification files under a top-level `specifications/` directory.

Each YAML entry should include both:

- `description`: human-readable explanation of what the signature represents and why it matters.
- `signature`: stable machine-readable structure used for matching, grouping, or later hashing.

The early version should keep files directly inside `specifications/`, not in subdirectories. If the number of signature types grows, the files can later be moved into subdirectories such as `specifications/dimensions/` and `specifications/composites/`.

## Guiding Distinction

Separate these concepts:

- **Dimension signature**
  - A narrow signature for one architectural dimension.
  - Examples: parent relationship shape, parent datastreams, child-object profile.

- **Composite architecture signature**
  - A calculated signature made from selected dimension signatures.
  - This is the likely replacement or refinement for the current overall object-architecture signature.

- **Observation metadata**
  - Evidence-quality and scan-context information.
  - Examples: public-API-only scope, sampled item count, truncated child fetches.
  - This should inform confidence, but should not usually define architecture identity.

## Project Context From README

This project identifies common object architectures in the Brown Digital Repository.

The practical purpose is ingest planning: if an architecture is common in the BDR, it is more likely to be a pattern the repository already supports without custom development.

For this plan, ignore the current implementation details and focus on a future-facing specification vocabulary that documents observed BDR behavior. The specifications should help explain what exists now, while leaving room for human-entered context such as `standard`, `non_standard`, `deprecated`, or local notes.

## Candidate Dimension Signatures

### 1. Parent Relationship Signature

Represents how the top-level object relates to direct child objects.

Initial file:

```text
specifications/parent_relationship_signatures.yaml
```

Initial fields:

- `has_children`
  - Boolean.
  - `true` when the sampled parent has observed direct children.
  - `false` when the sampled parent appears standalone through public API sampling.
- `ordered_children`
  - Boolean.
  - `true` when child ordering is observed as structurally meaningful, likely through pagination/order fields such as `rel_has_pagination_ssim`.
  - `false` when no ordering evidence is observed.

This dimension answers questions like:

- Is this a standalone object?
- Is this a parent object with direct children?
- Are the children page-like and ordered?

Fields such as `child_relation_type` and `membership_context` are not part of the initial direction. Direct child status can be treated as implied by the sampled parent/child lookup. Collection membership is important sampling context, but it should not define the parent relationship signature unless later review shows it changes architecture identity.

### 2. Object Definition Signature

Represents an object's own type and datastream inventory. This applies to both parent objects and child objects.

Initial file:

```text
specifications/object_definition_signatures.yaml
```

Initial fields:

- `object_type`
  - The BDR object type for the object whose datastreams are being described.
  - This should be derived from the public API / Search API object-type field, currently observed in project code as `object_type`.
  - This can describe either a parent object or a child object.
- `typeOfResource`
  - The resource type when available from descriptive metadata or API output.
  - Include this when it is available; leave it absent or unknown when it is not available through the public API evidence being used.
- `has_parent`
  - Boolean.
  - `true` when the object is observed as a child of another object.
  - `false` when the object is observed as a top-level object in the sampled context.
- `has_children`
  - Boolean.
  - `true` when the object has observed direct children.
  - `false` when no direct children are observed through the available API evidence.
- `is_ordered`
  - Boolean.
  - `true` when the object participates in an observed ordering relationship, such as ordered children or pagination.
  - `false` when no ordering evidence is observed.
- `datastream_ids`
  - The observed datastream IDs for the object.
  - These should be derived from the datastream inventory exposed by the API, currently observed in project code as `datastreams_ssi`.
  - If MIME type is available for a datastream, include it as part of the datastream detail rather than treating MIME type as merely external variation.

This dimension answers questions like:

- Is this a PDF-like object?
- Is this an image-like object?
- Does descriptive metadata identify a `typeOfResource`?
- Is the object observed as a parent object, child object, or top-level standalone object?
- Does the object participate in ordering?
- Does this object include only metadata datastreams, or also content-bearing datastreams?
- Which datastream IDs and MIME types are actually observed for this object type?

For now, codify what actually exists. Do not try to declare `required_datastream_ids` or `optional_datastream_ids` yet. Those categories are worth future review, but they require interpretation beyond the observed public-API evidence.

### 3. Open Access Signature

Represents rights/open-access characteristics. This is different from visibility: visibility describes what the public API allowed us to observe; open access describes license and embargo status.

Initial file:

```text
specifications/open_access_signatures.yaml
```

Initial fields:

- `license`
  - License or rights statement when available.
- `current_embargo_status`
  - Current embargo status when available.
  - This is likely not fully visible through the public BDR API, so early values may need to distinguish observed values from unknown values.

### 4. Visibility Signature

Represents access or discoverability characteristics.

This may need to remain future-facing if the initial work uses only public BDR APIs. Public API results can confirm that something is publicly discoverable, but cannot fully describe hidden, private, embargoed, or role-restricted material.

Initial file:

```text
specifications/visibility_signatures.yaml
```

Initial public-API field/value:

- `visibility_scope`
  - Use `public_api_observed`.

Initial description:

- `Object was visible through public API sampling; non-public variants are out of scope.`

### 5. Auxiliary Relationship Signature

Represents relationships that may not be direct parent-child membership but still affect architecture.

Initial file:

```text
specifications/auxiliary_relationships_signatures.yaml
```

Initial fields:

- `has_derivations`
- `has_transcripts`
- `has_translations`
- `has_annotations`

These relationships should be first-class dimensions in the specification vocabulary. Whether they participate in every composite architecture signature can be decided signature-by-signature.

## Specification File Structure

Use multiple flat YAML files, all directly inside `specifications/`.

This is the decided direction because the core idea is dimensional: relationship signatures, object-definition signatures, open-access signatures, visibility signatures, auxiliary relationship signatures, and composite signatures are conceptually different things. Separate files make those distinctions visible while keeping the initial directory structure simple.

```text
specifications/parent_relationship_signatures.yaml
specifications/object_definition_signatures.yaml
specifications/open_access_signatures.yaml
specifications/visibility_signatures.yaml
specifications/auxiliary_relationships_signatures.yaml
specifications/composite_architecture_signatures.yaml
```

Each individual signature should have a stable identifier. The existing code's hash-based identifier approach is a good model: serialize the `signature` deterministically, hash it, and store the resulting short hash with the entry.

For planning purposes, use `signature_hash` as the field name. The exact hash values below are placeholders.

Each signature entry should also include up to three exemplar BDR PIDs. These examples are human-review anchors, not part of the signature identity.

Initial conceptual shapes:

```yaml
# specifications/parent_relationship_signatures.yaml
schema_version: 1
signature_type: parent_relationship

signatures:
  parent_with_many_ordered_children:
    signature_hash: hash_parent_001
    description: Top-level object has observed direct children with meaningful ordering.
    exemplar_pids:
      - bdr:example_parent_001
      - bdr:example_parent_002
      - bdr:example_parent_003
    signature:
      has_children: true
      ordered_children: true

  standalone_object:
    signature_hash: hash_parent_002
    description: Top-level object has no observed direct children.
    exemplar_pids:
      - bdr:example_standalone_001
      - bdr:example_standalone_002
      - bdr:example_standalone_003
    signature:
      has_children: false
      ordered_children: false
```

```yaml
# specifications/object_definition_signatures.yaml
schema_version: 1
signature_type: object_definition

signatures:
  metadata_only_parent:
    signature_hash: hash_object_001
    description: Parent-like object with descriptive/control datastreams but no primary binary content datastream.
    exemplar_pids:
      - bdr:example_object_001
      - bdr:example_object_002
      - bdr:example_object_003
    signature:
      object_type: implicit-set
      typeOfResource: mixed material
      has_parent: false
      has_children: true
      is_ordered: true
      datastream_ids:
        - MODS
        - RELS-EXT
        - rightsMetadata

  image_child_object:
    signature_hash: hash_object_002
    description: Image-like child object with JP2 and thumbnail derivatives.
    exemplar_pids:
      - bdr:example_image_001
      - bdr:example_image_002
      - bdr:example_image_003
    signature:
      object_type: image
      typeOfResource: still image
      has_parent: true
      has_children: false
      is_ordered: true
      datastream_ids:
        - JP2
        - MODS
        - RELS-EXT
        - rightsMetadata
        - thumbnail
      datastream_details:
        JP2:
          mime_type: image/jp2
        thumbnail:
          mime_type: image/jpeg
```

```yaml
# specifications/open_access_signatures.yaml
schema_version: 1
signature_type: open_access

signatures:
  public_domain_or_open_license:
    signature_hash: hash_open_access_001
    description: Object has an observed license or rights statement indicating open access.
    exemplar_pids:
      - bdr:example_open_001
      - bdr:example_open_002
      - bdr:example_open_003
    signature:
      license: observed_license_or_rights_statement
      current_embargo_status: not_observed_or_not_embargoed

  unknown_open_access_status:
    signature_hash: hash_open_access_002
    description: Public API evidence does not establish license or current embargo status.
    exemplar_pids:
      - bdr:example_unknown_access_001
      - bdr:example_unknown_access_002
      - bdr:example_unknown_access_003
    signature:
      license: unknown
      current_embargo_status: unknown
```

```yaml
# specifications/visibility_signatures.yaml
schema_version: 1
signature_type: visibility

signatures:
  public_api_observed:
    signature_hash: hash_visibility_001
    description: Object was visible through public API sampling; non-public variants are out of scope.
    exemplar_pids:
      - bdr:example_visible_001
      - bdr:example_visible_002
      - bdr:example_visible_003
    signature:
      visibility_scope: public_api_observed
```

```yaml
# specifications/auxiliary_relationships_signatures.yaml
schema_version: 1
signature_type: auxiliary_relationships

signatures:
  no_observed_auxiliary_relationships:
    signature_hash: hash_auxiliary_001
    description: No derivation, transcript, translation, or annotation relationships were observed.
    exemplar_pids:
      - bdr:example_aux_none_001
      - bdr:example_aux_none_002
      - bdr:example_aux_none_003
    signature:
      has_derivations: false
      has_transcripts: false
      has_translations: false
      has_annotations: false

  observed_transcript_relationship:
    signature_hash: hash_auxiliary_002
    description: A transcript relationship was observed.
    exemplar_pids:
      - bdr:example_transcript_001
      - bdr:example_transcript_002
      - bdr:example_transcript_003
    signature:
      has_derivations: false
      has_transcripts: true
      has_translations: false
      has_annotations: false
```

```yaml
# specifications/composite_architecture_signatures.yaml
schema_version: 1
signature_type: composite_architecture

signatures:
  metadata_parent_with_children:
    signature_hash: hash_composite_001
    description: Compound object architecture with a metadata/control parent and observed direct children.
    narrative: Combines a parent/child relationship, object definition, open-access evidence, public-API visibility, and auxiliary-relationship evidence into one architecture identifier.
    exemplar_pids:
      - bdr:example_composite_001
      - bdr:example_composite_002
      - bdr:example_composite_003
    signature:
      parent_relationship_signature: parent_with_many_ordered_children
      parent_relationship_signature_hash: hash_parent_001
      parent_object_definition_signature: metadata_only_parent
      parent_object_definition_signature_hash: hash_object_001
      open_access_signature: public_domain_or_open_license
      open_access_signature_hash: hash_open_access_001
      visibility_signature: public_api_observed
      visibility_signature_hash: hash_visibility_001
      auxiliary_relationships_signature: no_observed_auxiliary_relationships
      auxiliary_relationships_signature_hash: hash_auxiliary_001
```

Composite signatures should refer to dimension signatures by stable IDs and by the component `signature_hash` values.

The composite `signature_hash` could be calculated from the component hashes, plus any other fields that are intentionally part of composite identity. Human-readable `description`, `narrative`, and `exemplar_pids` should support review and documentation, but should not normally affect the composite hash.

## Suggested Initial Specification Set

Begin with a small starter vocabulary rather than trying to classify all BDR architectures at once.

Possible initial dimension signatures:

- `standalone_object`
- `parent_with_one_child`
- `parent_with_few_children`
- `parent_with_many_ordered_children`
- `metadata_only_parent`
- `pdf_object`
- `image_child_object`
- `public_domain_or_open_license`
- `public_api_observed`
- `no_observed_auxiliary_relationships`

Possible initial composite signatures:

- `standalone_pdf`
- `standalone_image`
- `metadata_parent_with_children`

## How To Evaluate On Individual Or Small Sets Of Collections

Without designing implementation yet, the conceptual workflow can be:

1. Select one or a few collections that appear internally consistent.
2. For a small sample of parent items, identify observed dimension signatures.
3. Compare the observed dimensions to the YAML descriptions.
4. Note where a dimension signature is too strict, too loose, or missing.
5. Only after review, define a composite architecture signature.

The review should capture both matches and mismatches. Mismatches may be more informative than matches because they reveal where the signature vocabulary is unclear.

## Answered Questions

- **Should datastream signatures distinguish required, optional, and derivative datastreams now?**
  - Not yet. For now, datastream signatures should codify observed datastream IDs.
  - Future review can add human interpretation about required, optional, content, metadata, and derivative datastreams.

- **Should MIME type be part of datastream signatures?**
  - Yes, if MIME type is available from the observed datastream inventory, include it in datastream detail.

- **Should exact child counts define architecture identity?**
  - No. Exact child counts are not relevant to architecture identity.

- **Should child ordering belong to the parent relationship signature?**
  - Yes. Ordering describes the parent/child relationship.

- **Should visibility be represented while using only the public BDR API?**
  - Yes, but in a limited way.
  - Use `visibility_scope: public_api_observed`.
  - The description should make clear that the object was visible through public API sampling and that non-public variants are out of scope.

- **Should auxiliary relationships be first-class dimensions?**
  - Yes. Add `specifications/auxiliary_relationships_signatures.yaml` with booleans for derivations, transcripts, translations, and annotations.

- **Should a composite signature be a strict combination of dimension signature IDs?**
  - Yes, for now. Use strict combinations in the spirit of documenting observed BDR behavior.

- **Should descriptions document observed behavior, recommended ingest patterns, or both?**
  - For now, descriptions should document observed BDR behavior.
  - Additional human-entered context can later indicate whether observed patterns are `standard`, `non_standard`, `deprecated`, or otherwise noteworthy.

## Open Questions

- **How should video streaming be represented?**
  - As video collections are analyzed, determine whether streaming can be inferred from a datastream, a Panopto URL in the BDR API response, or another field.
  - Decide whether streaming belongs in the object definition signature or a separate media-delivery signature.

- **Should each signature type eventually have an allowed-values YAML file?**
  - It would be useful to maintain a listing for each signature type showing all known values.
  - Over time, those lists could be annotated with human-entered status such as `standard`, `non_standard`, `deprecated`, or local context.

- **When should required and optional datastream interpretation be added?**
  - The current direction is to document observed datastream IDs first.
  - Later work can decide how to mark datastreams as required or optional for a given standard architecture.

- **How should open-access fields distinguish observed values from unknown values?**
  - License may be visible in public API responses, but current embargo status may not be.
  - The specification vocabulary should avoid implying that unknown embargo status means no embargo.

## Proposed Next Step

Create a small draft `specifications/` directory using multiple flat YAML files, with no more than four to six starter signatures.

Then review those signatures against one or two known collections before changing any implementation. The goal of that review should be vocabulary validation, not full architecture detection.
