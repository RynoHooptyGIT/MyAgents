---
name: file-to-markdown
description: Use when you need to read a non-text file Claude can't open natively — .docx, .xlsx, .pptx, .epub, .msg (Outlook), or transcribe audio — by converting it to Markdown via Microsoft MarkItDown. NOT for plain text/code (Read directly) or PDFs/images (Read handles those natively and with higher fidelity).
---

# File → Markdown (MarkItDown)

## Overview

Claude Code's Read tool opens text, code, PDF, images, and notebooks natively. It
**cannot** open Office and other binary document formats. This skill bridges that
gap by converting them to Markdown with [Microsoft MarkItDown](https://github.com/microsoft/markitdown),
which produces LLM-optimized Markdown you then Read into context.

## When to Use

- `.docx`, `.xlsx`, `.xls`, `.pptx` — Word / Excel / PowerPoint
- `.epub` — e-books
- `.msg` — Outlook messages (needs `outlook` extra)
- audio files — transcription (needs `audio-transcription` extra)
- messy `.html` you want as clean Markdown

## When NOT to Use

- Plain text, code, `.md`, `.csv`, `.json`, `.xml` → Read directly.
- PDFs and images → Read handles these natively, with better fidelity than MarkItDown.

## Convert

Run via `uv` — no global install, extras resolved on demand:

```bash
uv tool run --from 'markitdown[docx,xlsx,pptx]' markitdown "<input-path>" > "<output-dir>/<name>.md"
```

Then Read the resulting `.md` into context.

Pick extras by the file at hand to keep the install light:

| Need | `--from` extras |
|------|-----------------|
| Word / Excel / PowerPoint | `markitdown[docx,xlsx,pptx]` |
| + Outlook `.msg` | `markitdown[docx,xlsx,pptx,outlook]` |
| + audio transcription | `markitdown[audio-transcription]` |
| everything | `markitdown[all]` |

Write output to the session scratchpad, not the user's repo, unless asked to keep it.

## Notes & Limits

- Requires Python 3.10+. `[all]` pulls heavy OCR/audio deps — prefer minimal extras.
- `.xlsx` / `.pptx` conversion is lossy: tables flatten, slide layout drops. Fine for
  LLM ingest, not for fidelity-critical reproduction.
- Untrusted files: MarkItDown has had path/SSRF advisories — `uv tool run` always
  fetches the latest published version, which mitigates stale-version risk.
- MIT licensed.
