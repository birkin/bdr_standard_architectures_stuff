## 2026-05-23

- Re the line: """- Uses `--sample-strategy` to choose `first`, `evenly-spaced`, or `random`."""

  I'm thinking that for some of these arguments, there is a default. If so, indicate in the appropriate argument section what the default is, if it's not already there.

  Add this prompt to `bdr_standard_architectures/recent_prompts.md`.

- Ensure all default output paths are _not_ in the project-root (where the .git/ directory lives). Set all default output paths to the sibling directory of the project-root.

  Add this prompt to `bdr_standard_architectures/recent_prompts.md`.
