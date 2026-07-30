# Project-level skill customizations

Files in this directory override the defaults from vendored skills. Each
file is named `<skill-name>.toml` and merges into the corresponding
`team/workflows/*/*/customize.toml` or `team/core-skills/*/customize.toml`
using bmad's merge rules:

- Strings replace.
- Lists append.
- Tables merge key-by-key.
- Arrays of tables merge by `id`; matching `id` replaces, new `id` appends.

`*.example.toml` files are copy-and-edit templates — the loader ignores them.

> TODO: loader — team/custom/ merge is convention-only until scripts/team-check.sh
> or the skill loader picks it up. Track separately.
