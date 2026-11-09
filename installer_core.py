"""Safe, verified installer engine compatible with Reawakened Patcher v0.4 manifests."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from patcher import PatcherError, load_manifest, contained_file, rel_path, patch_path, asset_path


def _check_sha(file: Path, expected: str, title: str):
    h = hashlib.sha256()
    with file.open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    if h.hexdigest().lower() != expected.lower():
        raise PatcherError(f'File verification failed: {title}. Ensure you selected the correct clean game files.')


def normalize_clean(folder: str | Path) -> Path:
    root = Path(folder).expanduser().resolve()
    if root.name.lower() == 'dvdroot_ps4':
        return root.parent
    if (root / 'dvdroot_ps4').is_dir():
        return root
    raise PatcherError('Choose the folder containing dvdroot_ps4, or dvdroot_ps4 itself.')


def install_package(clean_input: str | Path, package_input: str | Path, output_input: str | Path,
                    xdelta_input: str | Path, progress=None, log=None) -> dict:
    """Install to a NEW folder, with preflight and SHA-256 verification, using staging.

    progress(done: int, total: int, label: str) and log(text) are optional callbacks.
    Output cannot already exist. Original files are never modified.
    """
    progress = progress or (lambda done, total, label: None)
    log = log or (lambda line: None)
    clean = normalize_clean(clean_input)
    pkg = Path(package_input).expanduser().resolve()
    output = Path(output_input).expanduser().resolve()
    exe = Path(xdelta_input).expanduser()
    if not exe.is_file():
        found = shutil.which(str(xdelta_input))
        if found:
            exe = Path(found)
        else:
            raise PatcherError('xdelta3.exe was not found. Select a working Windows xdelta3.exe.')
    if not pkg.is_dir():
        raise PatcherError('Patch package folder does not exist.')
    doc = load_manifest(pkg / 'manifest.json')
    if doc.get('incomplete_missing_original_count', 0):
        raise PatcherError('The patch package is incomplete and cannot be installed.')
    entries = doc['files']
    if not entries:
        raise PatcherError('The package contains no files.')
    if output.exists():
        raise PatcherError('Output already exists. Choose a different/new destination folder.')
    if output == clean or output.is_relative_to(clean) or clean.is_relative_to(output):
        raise PatcherError('Output must be outside the original Bloodborne directory.')
    if output == pkg or output.is_relative_to(pkg) or pkg.is_relative_to(output):
        raise PatcherError('Output must be separate from the patch package.')

    total = len(entries) * 2
    counter = 0
    log(f'Package: {pkg}')
    log(f'Originals: {clean / "dvdroot_ps4"}')
    log(f'Output: {output}')
    log(f'Files in manifest: {len(entries)}')
    log('Checking all source files and hashes...')
    # Preflight checks; report progress even during validation of large source files.
    for e in entries:
        name = e['path']
        rp = rel_path(name)
        if e['kind'] == 'patch':
            original = contained_file(clean, rp)
            patch = contained_file(pkg, patch_path(e['patch']))
            if not original.is_file():
                raise PatcherError(f'Original game file missing: {name}')
            if not patch.is_file():
                raise PatcherError(f'Patch data missing: {e["patch"]}')
            _check_sha(original, e['original_sha256'], name)
        else:
            asset = contained_file(pkg, asset_path(e['asset']))
            if not asset.is_file():
                raise PatcherError(f'Extra asset missing: {e["asset"]}')
            _check_sha(asset, e['patched_sha256'], name)
        counter += 1
        progress(counter, total, 'Verifying source files')
    log('Source verification passed. Installing to a temporary folder...')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.reawakened_install_', dir=output.parent)).resolve()
    try:
        for e in entries:
            name = e['path']
            rp = rel_path(name)
            target = contained_file(stage, rp)
            target.parent.mkdir(parents=True, exist_ok=True)
            if e['kind'] == 'patch':
                original = contained_file(clean, rp)
                patch = contained_file(pkg, patch_path(e['patch']))
                proc = subprocess.run(
                    [str(exe), '-d', '-f', '-s', str(original), str(patch), str(target)],
                    capture_output=True, text=True, errors='replace',
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if proc.returncode:
                    raise PatcherError(f'xdelta3 failed for {name}: {proc.stderr[-1200:]}')
            else:
                shutil.copyfile(contained_file(pkg, asset_path(e['asset'])), target)
            _check_sha(target, e['patched_sha256'], name)
            counter += 1
            progress(counter, total, 'Applying and verifying patches')
            if counter % 25 == 0 or counter == total:
                log(f'{counter // 2} / {len(entries)} files installed and verified')
        stage.rename(output)
        log('INSTALLATION COMPLETE — all installed files matched the expected hashes.')
        return {'output': str(output), 'verified_files': len(entries), 'patches': sum(e['kind'] == 'patch' for e in entries),
                'extras': sum(e['kind'] == 'extra' for e in entries)}
    finally:
        if stage.exists():
            shutil.rmtree(stage)
