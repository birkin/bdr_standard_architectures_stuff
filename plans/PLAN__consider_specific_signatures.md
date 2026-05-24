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

- `parent_object_type`
  - The BDR object type of the top-level object being analyzed.
  - This should be derived from the public API / Search API object-type field, currently observed in project code as `object_type`.
  - This identifies whether the parent is something like an image, PDF-like object, implicit set, collection-like object, or another BDR object category.
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

### 2. Object Datastream Signature

Represents an object's own datastream inventory. This applies to both parent objects and child objects.

Initial file:

```text
specifications/object_datastream_signatures.yaml
```

Initial fields:

- `object_type`
  - The BDR object type for the object whose datastreams are being described.
  - This should be derived from the public API / Search API object-type field, currently observed in project code as `object_type`.
  - This can describe either a parent object or a child object.
- `datastream_ids`
  - The observed datastream IDs for the object.
  - These should be derived from the datastream inventory exposed by the API, currently observed in project code as `datastreams_ssi`.
  - If MIME type is available for a datastream, include it as part of the datastream detail rather than treating MIME type as merely external variation.

This dimension answers questions like:

- Is this a PDF-like object?
- Is this an image-like object?
- Does this object include only metadata datastreams, or also content-bearing datastreams?
- Which datastream IDs and MIME types are actually observed for this object type?

For now, codify what actually exists. Do not try to declare `required_datastream_ids` or `optional_datastream_ids` yet. Those categories are worth future review, but they require interpretation beyond the observed public-API evidence.

### 3. Child Profile Signature

Represents the architecture of child objects as a group, not as individual PIDs.

Possible fields:

- `child_groups`
- `child_object_type`
- `child_datastream_signature_ref`
- `display_label_bucket`
- `count_bucket`
- `ordered`

This dimension answers questions like:

- Are there many image children?
- Are there mixed child types, such as image children plus one PDF or TEI child?
- Do child datastreams match a known child-object signature?
- Is child ordering structurally significant?

Exact child counts should not define architecture identity. Use count buckets where useful, and treat exact counts as observation/reporting metadata only.

Child ordering belongs in both the parent relationship signature and the child profile signature because it describes the parent/child relationship and the profile of the child group.

### 4. Open Access Signature

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

### 5. Visibility Signature

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

### 6. Presentation Or Navigation Signature

Represents aspects that affect display or user navigation, even if they are not core preservation architecture.

Possible fields:

- `viewer_pattern`
- `ordered_sequence`
- `page_like_children`
- `representative_thumbnail`
- `streaming_or_download_pattern`

This may be useful because two objects can have similar datastreams but require different presentation expectations.

### 7. Auxiliary Relationship Signature

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

This is the decided direction because the core idea is dimensional: relationship signatures, datastream signatures, child signatures, open-access signatures, visibility signatures, auxiliary relationship signatures, and composite signatures are conceptually different things. Separate files make those distinctions visible while keeping the initial directory structure simple.

```text
specifications/parent_relationship_signatures.yaml
specifications/object_datastream_signatures.yaml
specifications/child_profile_signatures.yaml
specifications/open_access_signatures.yaml
specifications/visibility_signatures.yaml
specifications/auxiliary_relationships_signatures.yaml
specifications/composite_architecture_signatures.yaml
```

Initial conceptual shape:

```yaml
# specifications/object_datastream_signatures.yaml
schema_version: 1
signature_type: object_datastream

signatures:
  metadata_only_parent:
    description: Parent-like object with descriptive/control datastreams but no primary binary content datastream.
    signature:
      object_type: implicit-set
      datastream_ids:
        - MODS
        - RELS-EXT
        - rightsMetadata

  image_child_object:
    description: Image-like child object with JP2 and thumbnail derivatives.
    signature:
      object_type: image
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
# specifications/composite_architecture_signatures.yaml
schema_version: 1
signature_type: composite_architecture

signatures:
  metadata_parent_with_many_image_children:
    description: Compound object architecture with a metadata/control parent and many image-like child objects.
    signature:
      parent_relationship_signature: parent_with_many_ordered_children
      parent_datastream_signature: metadata_only_parent
      child_profile_signature: many_image_children
      open_access_signature: public_domain_or_open_license
      visibility_signature: public_api_observed
      auxiliary_relationships_signature: no_observed_auxiliary_relationships
```

Composite signatures should refer to dimension signatures by stable IDs.

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
- `many_image_children`
- `mixed_image_and_text_children`
- `public_domain_or_open_license`
- `public_api_observed`
- `no_observed_auxiliary_relationships`

Possible initial composite signatures:

- `standalone_pdf`
- `standalone_image`
- `metadata_parent_with_many_image_children`
- `metadata_parent_with_image_children_and_text_child`

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
  - Use count buckets where a child-profile summary needs to distinguish no children, one child, a few children, or many children.

- **Should child ordering belong to the parent relationship signature, the child profile signature, or both?**
  - Both. Ordering describes the parent/child relationship and also characterizes the child group.

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
  - Decide whether streaming belongs in the presentation/navigation signature, the object datastream signature, or a separate media-delivery signature.

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
