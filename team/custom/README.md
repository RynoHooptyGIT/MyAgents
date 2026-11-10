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

The loader (`_bmad/scripts/config_utils.py`) reads overrides from this
directory directly; a file here takes effect immediately, and wins over an
equivalent override left in `_bmad/custom/` for backward compatibility.
