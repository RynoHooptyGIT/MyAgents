#!/usr/bin/env bash
# =============================================================================
# scripts/lib/install-manifest.sh — sourced library (bash 3.2 compatible)
# =============================================================================
# apply_manifest SRC_ROOT DST_ROOT [--dry-run] [--manifest FILE] [--group NAME[,NAME]]
#
# Reads templates/install-manifest.txt (mode<TAB>src<TAB>dst[<TAB>group] per
# line; see the header of that file for the format) under SRC_ROOT and installs
# each entry into DST_ROOT. Used by scripts/setup.sh (fresh install) and
# scripts/team-update.sh (update) so both ship the same tooling.
#
#   copy  copy, overwriting dst
#   init  copy only if dst is absent — prints "kept <dst>" otherwise
#   exec  copy, overwriting dst, then chmod +x
#
# The optional 4th column is the entry's group (`core` when absent). With
# --group only entries in the named group(s) are applied (repeatable or
# comma-separated); without it every entry is applied.
#
# Prints one line per file: "installed <dst>", "kept <dst>" or (dry run)
# "would-install <dst>", with <dst> relative to DST_ROOT. A src glob that matches
# nothing is skipped with a warning on stderr. Returns 0 unless a copy fails
# (1) or the arguments/manifest are unusable (2). Safe under `set -e`/`set -u`
# and with spaces in either root.
# =============================================================================

_apply_manifest_usage() {
    echo "usage: apply_manifest SRC_ROOT DST_ROOT [--dry-run] [--manifest FILE] [--group NAME[,NAME]]" >&2
}

# _apply_manifest_one MODE SRC_FILE DST DST_ROOT DRY_RUN
_apply_manifest_one() {
    local mode="$1" src_file="$2" dst="$3" dst_root="$4" dry_run="$5"
    local base="${src_file##*/}" rel target

    case "$dst" in
        */) rel="${dst}${base}" ;;
        *)  rel="$dst" ;;
    esac
    target="$dst_root/$rel"

    if [ "$mode" = "init" ] && [ -e "$target" ]; then
        echo "kept $rel"
        return 0
    fi
    if [ "$dry_run" -eq 1 ]; then
        echo "would-install $rel"
        return 0
    fi

    if ! mkdir -p "${target%/*}" 2>/dev/null; then
        echo "apply_manifest: error: cannot create directory ${target%/*}" >&2
        return 1
    fi
    if ! cp "$src_file" "$target" 2>/dev/null; then
        echo "apply_manifest: error: copy failed: $src_file -> $target" >&2
        return 1
    fi
    if [ "$mode" = "exec" ] && ! chmod +x "$target" 2>/dev/null; then
        echo "apply_manifest: error: chmod +x failed: $target" >&2
        return 1
    fi
    echo "installed $rel"
    return 0
}

apply_manifest() {
    local src_root="" dst_root="" manifest="" dry_run=0 groups=""

    while [ $# -gt 0 ]; do
        case "$1" in
            --dry-run)    dry_run=1 ;;
            --manifest)   shift; manifest="${1:-}" ;;
            --manifest=*) manifest="${1#--manifest=}" ;;
            --group)      shift; groups="${groups:+$groups,}${1:-}" ;;
            --group=*)    groups="${groups:+$groups,}${1#--group=}" ;;
            -*) echo "apply_manifest: unknown option: $1" >&2; _apply_manifest_usage; return 2 ;;
            *)
                if [ -z "$src_root" ]; then
                    src_root="$1"
                elif [ -z "$dst_root" ]; then
                    dst_root="$1"
                else
                    echo "apply_manifest: unexpected argument: $1" >&2; _apply_manifest_usage; return 2
                fi
                ;;
        esac
        shift
    done

    if [ -z "$src_root" ] || [ -z "$dst_root" ]; then
        _apply_manifest_usage
        return 2
    fi
    if [ ! -d "$src_root" ]; then
        echo "apply_manifest: source root is not a directory: $src_root" >&2
        return 2
    fi
    [ -n "$manifest" ] || manifest="$src_root/templates/install-manifest.txt"
    if [ ! -f "$manifest" ]; then
        echo "apply_manifest: manifest not found: $manifest" >&2
        return 2
    fi

    local rc=0 lineno=0 matched mode src dst group f src_dir

    # fd 3 keeps the manifest separate from stdin (so nothing in the loop can eat it).
    while IFS=$'\t' read -r mode src dst group <&3 || [ -n "${mode:-}" ]; do
        lineno=$((lineno + 1))
        # Tolerate CRLF and trailing whitespace on the last field.
        group="${group%$'\r'}"
        group="${group%"${group##*[![:space:]]}"}"
        dst="${dst%$'\r'}"
        dst="${dst%"${dst##*[![:space:]]}"}"
        mode="${mode%$'\r'}"
        [ -n "$group" ] || group="core"

        case "$mode" in
            ''|'#'*) continue ;;
            copy|init|exec) ;;
            *)
                echo "apply_manifest: warning: line $lineno: unknown mode '$mode' — skipped" >&2
                continue
                ;;
        esac
        if [ -z "$src" ] || [ -z "$dst" ]; then
            echo "apply_manifest: warning: line $lineno: expected mode<TAB>src<TAB>dst — skipped" >&2
            continue
        fi
        if [ -n "$groups" ]; then
            case ",$groups," in
                *",$group,"*) ;;
                *) continue ;;
            esac
        fi
        case "$src" in
            /*|*/../*|../*)
                echo "apply_manifest: warning: line $lineno: src must be relative to the source root — skipped" >&2
                continue
                ;;
        esac
        case "$src" in
            *'*'*|*'?'*|*'['*)
                case "$dst" in
                    */) ;;
                    *)
                        echo "apply_manifest: warning: line $lineno: glob src '$src' needs a directory dst (trailing /) — skipped" >&2
                        continue
                        ;;
                esac
                ;;
        esac

        # Expand the basename glob with find (shell-agnostic, space-safe); results
        # are sorted so output order is stable.
        matched=0
        src_dir="$src_root/${src%/*}"
        [ "${src%/*}" = "$src" ] && src_dir="$src_root"
        if [ -d "$src_dir" ]; then
            while IFS= read -r f <&4; do
                [ -n "$f" ] || continue
                matched=$((matched + 1))
                _apply_manifest_one "$mode" "$f" "$dst" "$dst_root" "$dry_run" || rc=1
            done 4< <(find "$src_dir" -mindepth 1 -maxdepth 1 -type f -name "${src##*/}" 2>/dev/null | LC_ALL=C sort)
        fi

        if [ "$matched" -eq 0 ]; then
            echo "apply_manifest: warning: line $lineno: no match for '$src' under $src_root — skipped" >&2
        fi
    done 3< "$manifest"

    return $rc
}
