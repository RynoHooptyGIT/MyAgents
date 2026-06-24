#!/usr/bin/env python3
"""
compress.py — LLMLingua-2 prompt/context compressor.

Compresses large STATIC context (pasted logs, docs, RAG chunks) by 50-80% with
meaning preserved. This is for reference material, NOT for personas or the
user's own instruction — compressing instructions loses intent.

Usage:
    python scripts/compress.py --ratio 0.5 < big_context.txt
    python scripts/compress.py --ratio 0.33 -i input.txt -o compressed.txt
    echo "long text..." | python scripts/compress.py

--ratio is the fraction of tokens to KEEP (0.5 = halve it).

First run downloads the LLMLingua-2 model (~500 MB). Install deps once:
    pip install llmlingua

If llmlingua isn't installed, falls back to a cheap lexical squeeze (collapse
whitespace + drop stopwords) so the pipeline still works, and says so on stderr.
"""
import argparse
import sys


def llmlingua_compress(text: str, rate: float) -> str:
    from llmlingua import PromptCompressor  # type: ignore

    # LLMLingua-2: token-classification compressor, model-agnostic output.
    compressor = PromptCompressor(
        model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
        use_llmlingua2=True,
    )
    result = compressor.compress_prompt(text, rate=rate, force_tokens=["\n", ".", "?", "!"])
    return result["compressed_prompt"]


def lexical_fallback(text: str, rate: float) -> str:
    """No model available — collapse whitespace and thin low-information words.
    Crude, lossy, but dependency-free. Real savings come from llmlingua."""
    import re

    stop = {
        "the", "a", "an", "of", "to", "in", "on", "at", "for", "and", "or",
        "is", "are", "was", "were", "be", "been", "that", "this", "it", "as",
        "with", "by", "from", "we", "you", "i", "they", "he", "she",
    }
    text = re.sub(r"[ \t]+", " ", text)
    out_lines = []
    for line in text.splitlines():
        words = line.split(" ")
        # Keep code-ish / punctuation-heavy lines intact; only thin prose.
        if sum(c.isalpha() for c in line) < len(line) * 0.5:
            out_lines.append(line)
            continue
        kept = [w for w in words if w.lower().strip(".,;:") not in stop or not w.isalpha()]
        # Honor the keep-rate roughly by truncating if still over budget.
        if rate < 1.0:
            budget = max(1, int(len(kept) * rate / 0.7))  # 0.7 ≈ stopword share kept
            kept = kept[:budget] if budget < len(kept) else kept
        out_lines.append(" ".join(kept))
    return "\n".join(out_lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compress large context with LLMLingua-2.")
    ap.add_argument("--ratio", type=float, default=0.5,
                    help="Fraction of tokens to KEEP (0.5 = halve). Default 0.5.")
    ap.add_argument("-i", "--input", help="Input file (default: stdin).")
    ap.add_argument("-o", "--output", help="Output file (default: stdout).")
    args = ap.parse_args()

    text = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
    if not text.strip():
        print("compress.py: empty input", file=sys.stderr)
        return 1

    before = len(text)
    try:
        out = llmlingua_compress(text, args.ratio)
        engine = "llmlingua-2"
    except ImportError:
        out = lexical_fallback(text, args.ratio)
        engine = "lexical-fallback (pip install llmlingua for real compression)"
    except Exception as e:  # model/download/runtime error — degrade gracefully
        print(f"compress.py: llmlingua failed ({e}); using fallback", file=sys.stderr)
        out = lexical_fallback(text, args.ratio)
        engine = "lexical-fallback"

    after = len(out)
    pct = (1 - after / before) * 100 if before else 0
    print(f"compress.py: {engine} — {before} → {after} chars (-{pct:.0f}%)",
          file=sys.stderr)

    if args.output:
        open(args.output, "w", encoding="utf-8").write(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
