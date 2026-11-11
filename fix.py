#!/usr/bin/env python3
"""Build a local fixed extension from a user-supplied original. No dependencies."""
import argparse
import json
from pathlib import Path
import re
import shutil


def fix_parser(source):
    """Prefer the active modal ID over the background video's pathname ID."""
    pattern = re.compile(
        r"(?P<path>^[ \t]*const fromPath = url\.pathname\.match\(VIDEO_PATH\);\r?\n"
        r"[ \t]*if \(fromPath\) return fromPath\[1\];\r?\n)"
        r"(?P<modal>[ \t]*const modal = url\.searchParams\.get\('modal_id'\) \|\| url\.searchParams\.get\('modalId'\);\r?\n"
        r"[ \t]*if \(modal && /\^\\d\{5,\}\$/.test\(modal\)\) return modal;\r?\n)", re.M)
    updated, count = pattern.subn(lambda m: m['modal'] + m['path'], source)
    if count == 1:
        return updated
    if count == 0 and re.search(
        r"if \(modal && /\^\\d\{5,\}\$/.test\(modal\)\) return modal;\s*"
        r"const fromPath = url\.pathname\.match\(VIDEO_PATH\);", source):
        return source
    raise ValueError('Unsupported parser: expected exactly one matching URL parser. No output created.')


def build(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Output already exists. Choose a new output directory.')
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('Source and output must be separate directories, not nested.')
    parser = source / 'lib' / 'aweme-parse.js'
    updated = fix_parser(parser.read_bytes().decode('utf-8'))
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('manifest_version') != 3:
        raise ValueError('Expected a Manifest V3 extension.')
    manifest['name'] = '抖音视频下载助手（弹窗识别修复版）'
    # Local derivative build marker; not an official upstream release number.
    manifest['version'] = '1.1.2'
    manifest.pop('key', None)
    manifest.pop('update_url', None)
    shutil.copytree(source, output, ignore=shutil.ignore_patterns(
        '.git', '_metadata', 'node_modules', '.DS_Store', '*.crx', '*.zip'))
    (output / 'lib' / 'aweme-parse.js').write_bytes(updated.encode('utf-8'))
    (output / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return output


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('source', type=Path, help='Original unpacked extension directory')
    cli.add_argument('output', type=Path, help='New directory for the fixed local build')
    args = cli.parse_args()
    try:
        result = build(args.source, args.output)
    except (OSError, ValueError) as exc:
        cli.exit(1, f'Error: {exc}\n')
    print(f'Fixed extension created: {result}')


if __name__ == '__main__':
    main()
