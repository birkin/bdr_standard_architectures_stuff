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

## Candidate Dimension Signatures

### 1. Parent Relationship Signature

Represents how the top-level object relates to other objects.

Possible fields:

- `parent_object_type`
- `has_children`
- `child_relation_type`
- `child_count_bucket`
- `ordered_children`
- `membership_context`

This dimension answers questions like:

- Is this a standalone object?
- Is this a parent object with direct children?
- Are the children page-like and ordered?
- Is the object itself a child of another object?

### 2. Object Datastream Signature

Represents an object's own datastream inventory.

Possible fields:

- `object_type`
- `datastream_ids`
- `required_datastream_ids`
- `optional_datastream_ids`
- `content_datastream_ids`
- `metadata_datastream_ids`
- `derivative_datastream_ids`

This dimension answers questions like:

- Is this a PDF-like object?
- Is this an image-like object?
- Does this object include only metadata datastreams, or also content-bearing datastreams?
- Do MIME-type differences matter for this signature, or should they be reported as variation?

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

### 4. Visibility Signature

Represents access or discoverability characteristics.

This may need to remain future-facing if the initial work uses only public BDR APIs. Public API results can confirm that something is publicly discoverable, but cannot fully describe hidden, private, embargoed, or role-restricted material.

Possible fields:

- `visibility_scope`
- `discoverability`
- `download_access`
- `metadata_access`
- `content_access`
- `source`

Initial public-API value might be intentionally limited, such as:

- `visibility_scope: public_api_observed`
- `description: Object was visible through public API sampling; non-public variants are out of scope.`

### 5. Presentation Or Navigation Signature

Represents aspects that affect display or user navigation, even if they are not core preservation architecture.

Possible fields:

- `viewer_pattern`
- `ordered_sequence`
- `page_like_children`
- `representative_thumbnail`
- `streaming_or_download_pattern`

This may be useful because two objects can have similar datastreams but require different presentation expectations.

### 6. Auxiliary Relationship Signature

Represents relationships that may not be direct parent-child membership but still affect architecture.

Possible fields:

- `has_derivations`
- `has_transcripts`
- `has_translations`
- `has_annotations`
- `has_versions`

This should probably begin as secondary metadata, not part of the primary composite signature, unless review shows these relationships are central to standard ingest guidance.

## Proposal 1: Single YAML Registry File

Use one file:

```text
specifications/object_architecture_signatures.yaml
```

Conceptual shape:

```yaml
schema_version: 1
purpose: Human-readable registry of specific object-architecture signature dimensions and composite signatures.

dimension_signatures:
  parent_relationship:
    standalone_object:
      description: Object has no observed direct children and is treated as a standalone top-level item.
      signature:
        has_children: false
        child_relation_type: none
        child_count_bucket: none

  object_datastreams:
    pdf_object:
      description: Object has metadata/control datastreams plus a PDF content datastream.
      signature:
        datastream_ids:
          - MODS
          - PDF
          - RELS-EXT
          - rightsMetadata

  child_profiles:
    many_image_children:
      description: Parent has many image-like children, usually representing pages or ordered image components.
      signature:
        child_groups:
          - child_object_type: image
            count_bucket: many:10+
            child_datastream_signature_ref: image_child_object

composite_signatures:
  compound_object_with_image_children:
    description: Parent object with metadata/control datastreams and many image-like child objects.
    signature:
      dimensions:
        parent_relationship: parent_with_many_ordered_children
        parent_datastreams: metadata_only_parent
        child_profile: many_image_children
        visibility: public_api_observed
```

### Strengths

- **Simple start**: One file is easy to review and version-control.
- **Low ceremony**: No need to decide file boundaries too early.
- **Good for discussion**: Reviewers can see all proposed dimensions and composites together.
- **Easy to refactor later**: Entries can later be moved into separate files or subdirectories.

### Weaknesses

- **Can become large**: The file may become unwieldy as signature categories grow.
- **Merge conflicts**: Multiple people editing different signature categories may collide.
- **Weaker ownership boundaries**: It may be less obvious which section is authoritative for a given signature type.

### Best Use

This is best if the immediate goal is conceptual exploration and a small number of initial signatures.

## Proposal 2: Multiple Flat YAML Files In `specifications/`

Use several files, all directly inside `specifications/`:

```text
specifications/parent_relationship_signatures.yaml
specifications/object_datastream_signatures.yaml
specifications/child_profile_signatures.yaml
specifications/visibility_signatures.yaml
specifications/composite_architecture_signatures.yaml
```

Conceptual shape:

```yaml
# specifications/object_datastream_signatures.yaml
schema_version: 1
signature_type: object_datastream

signatures:
  metadata_only_parent:
    description: Parent-like object with descriptive/control datastreams but no primary binary content datastream.
    signature:
      datastream_ids:
        - MODS
        - RELS-EXT
        - rightsMetadata

  image_child_object:
    description: Image-like child object with JP2 and thumbnail derivatives.
    signature:
      datastream_ids:
        - JP2
        - MODS
        - RELS-EXT
        - rightsMetadata
        - thumbnail
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
      visibility_signature: public_api_observed
```

### Strengths

- **Clear separation**: Each file has one signature type.
- **Scales better**: New dimensions can be added without making one registry file enormous.
- **Easier review**: Reviewers can focus on parent relationships, datastreams, child profiles, or composites separately.
- **Natural migration path**: If needed, each file can later become a subdirectory category.

### Weaknesses

- **More structure upfront**: Requires naming conventions and cross-file references earlier.
- **Reference consistency**: Composite signatures must refer to dimension signatures by stable IDs.
- **Slightly higher review burden**: Understanding one composite may require opening several files.

### Best Use

This is best if the project expects signature dimensions to grow or if the team wants each dimension to be independently curated.

## Recommendation

Start with **Proposal 2: multiple flat YAML files** if the goal is to move toward real reusable specifications.

Reason:

- The core idea is dimensional: relationship signatures, datastream signatures, child signatures, visibility signatures, and composite signatures are conceptually different things.
- Separate files make that distinction visible.
- The directory still remains simple because there are no subdirectories at first.
- Composite signatures can explicitly show which dimension signatures they combine.

If the next step is still mostly brainstorming, use **Proposal 1** for one short-lived registry file, then split it once the vocabulary stabilizes.

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
- `public_api_observed`

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

## Open Questions

- Should datastream signatures distinguish required, optional, and derivative datastreams, or should they initially use only observed datastream IDs?
    - FEEDBACK: for now, only observed datastream IDs.
- Should MIME type be part of datastream signatures, or a variation reported outside the signature?
    - FEEDBACK: if we have it, let's include it.
- Should exact child counts ever matter, or should count buckets always define architecture identity?
    - FEEDBCK: ignore exact counts; not relevant.
- Should child ordering be part of the parent relationship signature, the child profile signature, or both?
    - FEEDBACK: let's say both.
- Should visibility remain out of the composite signature until non-public API data is available?
    - FEEDBACK: see my context notes elsewere for very limited "public" usage in the signature.
- Should auxiliary relationships such as transcripts, translations, annotations, derivations, and versions become first-class dimensions?
    - FEEDBACK: answered in my context notes.
- Should a composite signature be a strict combination of dimension signature IDs, or should it allow overrides and local refinements?
    - FEEDBACK: for now -- let's say strict combination for now -- in the spirit of documenting what exists.
- Should human-readable descriptions describe observed BDR behavior, recommended ingest patterns, or both?
    - FEEDBACK: for now, observed BDR behavior -- but there will be additional human-entered context indicating "standard"/"deprecated" content.

## Proposed Next Step

Create a small draft `specifications/` directory using either Proposal 1 or Proposal 2, with no more than four to six starter signatures.

Then review those signatures against one or two known collections before changing any implementation. The goal of that review should be vocabulary validation, not full architecture detection.
