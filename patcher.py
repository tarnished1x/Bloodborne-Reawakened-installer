#!/usr/bin/env python3
"""Bloodborne: Reawakened patch tool. Requires user-supplied xdelta3 executable.

No Bloodborne original data is bundled in this tool.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile

FORMAT_VERSION = 2

class PatcherError(Exception):
    pass

def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(2 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def rel_path(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or '\x00' in name:
        raise PatcherError(f'Ungueltiger relativer Pfad: {name!r}')
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('', '.', '..') for x in name.split('/')):
        raise PatcherError(f'Unsicherer Pfad: {name!r}')
    if p.parts[0] != 'dvdroot_ps4':
        raise PatcherError(f'Pfad muss mit dvdroot_ps4/ beginnen: {name}')
    return Path(*p.parts)

def patch_path(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or '\x00' in name:
        raise PatcherError(f'Ungueltiger Patchpfad: {name!r}')
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('', '.', '..') for x in name.split('/')) or p.parts[0] != 'patches':
        raise PatcherError(f'Unsicherer Patchpfad: {name}')
    return Path(*p.parts)

def asset_path(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or '\x00' in name:
        raise PatcherError(f'Ungueltiger Assetpfad: {name!r}')
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('', '.', '..') for x in name.split('/')) or p.parts[0] != 'extras':
        raise PatcherError(f'Unsicherer Assetpfad: {name}')
    return Path(*p.parts)

def approved_extras(path):
    if path is None:
        return set()
    p = Path(path)
    if not p.is_file():
        raise PatcherError(f'Freigabeliste nicht vorhanden: {p}')
    names = set()
    for line in p.read_text(encoding='utf-8-sig').splitlines():
        name = line.strip()
        if not name or name.startswith('#'):
            continue
        rel_path(name)
        if name.casefold() in (x.casefold() for x in names):
            raise PatcherError(f'Doppelter Eintrag in Freigabeliste: {name}')
        names.add(name)
    return names

def contained_file(root, rel):
    root = Path(root).resolve()
    dest = (root / rel).resolve()
    if not dest.is_relative_to(root):
        raise PatcherError(f'Symlink oder Pfadverlassen erkannt: {rel}')
    return dest

def check_hash(actual, expected, desc):
    if actual.lower() != expected.lower():
        raise PatcherError(f'SHA-256 stimmt nicht: {desc}. Erwartet {expected}, gefunden {actual}.')

def load_manifest(path):
    with open(path, 'r', encoding='utf-8') as f:
        doc = json.load(f)
    if doc.get('format') != FORMAT_VERSION or not isinstance(doc.get('files'), list):
        raise PatcherError('Ungueltiges Manifestformat.')
    seen = set()
    for e in doc['files']:
        kind = e.get('kind')
        if kind == 'patch':
            if set(e) != {'kind','path','patch','original_sha256','patched_sha256'}:
                raise PatcherError('Ungueltiger Patch-Eintrag.')
            patch_path(e['patch'])
            hashes = ('original_sha256', 'patched_sha256')
        elif kind == 'extra':
            if set(e) != {'kind','path','asset','patched_sha256'}:
                raise PatcherError('Ungueltiger Zusatzdatei-Eintrag.')
            asset_path(e['asset'])
            hashes = ('patched_sha256',)
        else:
            raise PatcherError('Unbekannter Eintragstyp.')
        rel_path(e['path'])
        key = e['path'].casefold()
        if key in seen:
            raise PatcherError(f'Doppelter Dateipfad im Manifest: {e["path"]}')
        seen.add(key)
        for k in hashes:
            h = e[k]
            if not isinstance(h, str) or len(h) != 64 or any(c not in '0123456789abcdefABCDEF' for c in h):
                raise PatcherError(f'Ungueltiger Hash fuer {e["path"]}')
    return doc

def run_xdelta(exe, args):
    proc = subprocess.run([str(exe), *map(str, args)], capture_output=True, text=True)
    if proc.returncode:
        raise PatcherError(f'xdelta3 fehlgeschlagen (Code {proc.returncode}): {proc.stderr[-1200:]}')

def build(args):
    clean = Path(args.clean).resolve()
    mod = Path(args.modified).resolve()
    pkg = Path(args.package).resolve()
    if not clean.is_dir() or not mod.is_dir():
        raise PatcherError('Original- und Mod-Ordner muessen existieren.')
    if pkg == clean or pkg == mod or pkg.is_relative_to(clean) or pkg.is_relative_to(mod):
        raise PatcherError('Paket muss ausserhalb der Eingabeordner liegen.')
    if pkg.exists() and any(pkg.iterdir()):
        raise PatcherError('Paketordner muss leer sein (keine alten Patches mischen).')
    pkg.mkdir(parents=True, exist_ok=True)
    files = []
    missing = []
    approvals = approved_extras(args.approved_extras)
    used_approvals = set()
    all_files = sorted([p for p in mod.rglob('*') if p.is_file()])
    if not all_files:
        raise PatcherError('Mod-Ordner enthaelt keine Dateien.')
    for i, updated in enumerate(all_files, 1):
        rel = updated.relative_to(mod)
        rel_posix = rel.as_posix()
        rel_path(rel_posix)
        original = contained_file(clean, rel)
        if not original.is_file():
            if rel_posix in approvals:
                used_approvals.add(rel_posix)
                asset_rel = f'extras/{i:05d}.bin'
                extra_target = contained_file(pkg, asset_path(asset_rel))
                extra_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(updated, extra_target)
                verified_hash = sha256(updated)
                check_hash(sha256(extra_target), verified_hash, rel_posix+' (Zusatzdatei)')
                files.append({'kind':'extra','path':rel_posix,'asset':asset_rel,'patched_sha256':verified_hash})
                print(f'FREIGEGEBENE Zusatzdatei aufgenommen: {rel_posix}')
            else:
                missing.append(rel_posix)
                print(f'NICHT FREIGEGEBEN / Original fehlt: {rel_posix}')
            continue
        new_hash, old_hash = sha256(updated), sha256(original)
        if new_hash == old_hash:
            print(f'Unveraendert (weggelassen): {rel_posix}')
            continue
        patch_rel = f'patches/{i:05d}.vcdiff'
        patch_file = contained_file(pkg, patch_path(patch_rel))
        patch_file.parent.mkdir(parents=True, exist_ok=True)
        run_xdelta(args.xdelta, ['-e','-f','-s', original, updated, patch_file])
        # Verify using original, before trusting patch.
        with tempfile.TemporaryDirectory(prefix='reawakened_check_') as tmp:
            verified = Path(tmp) / 'decoded'
            run_xdelta(args.xdelta, ['-d','-f','-s', original, patch_file, verified])
            check_hash(sha256(verified), new_hash, rel_posix + ' (Patch-Roundtrip)')
        files.append({'kind':'patch','path':rel_posix,'patch':patch_rel,'original_sha256':old_hash,'patched_sha256':new_hash})
        print(f'Patch erzeugt und geprueft: {rel_posix}')
    unused = approvals - used_approvals
    if unused:
        raise PatcherError('Freigabeliste enthaelt Pfade, die nicht als fehlende Originaldateien gefunden wurden: '+', '.join(sorted(unused)[:10]))
    if missing:
        (pkg/'EXTRAS_CANDIDATES.txt').write_text('# Nur selbst erstellte oder nachweislich zur Weitergabe freigegebene Dateien freigeben.\n'+'\n'.join(missing)+'\n', encoding='utf-8')
        report = ('Diese Dateien sind im privaten Modbuild, aber nicht im angegebenen Originalordner vorhanden.\n'
                  'Sie wurden NICHT gepatcht oder ins Release aufgenommen.\n'
                  'Pruefe fuer jede Datei die Originalquelle, den Pfad und die Nutzungsrechte.\n'
                  'ACHTUNG: Dieses Patchpaket ist UNVOLLSTAENDIG und noch NICHT zur Veroeffentlichung geeignet!\n\n'
                  + '\n'.join(missing) + '\n')
        (pkg/'MISSING_ORIGINALS_REVIEW.txt').write_text(report, encoding='utf-8')
        print('WARNUNG: %d NICHT freigegebene Dateien ohne Original! Details: %s' % (len(missing), pkg / 'MISSING_ORIGINALS_REVIEW.txt'))
    manifest = {'format':FORMAT_VERSION,'title':'Bloodborne: Reawakened','files':files}
    if missing:
        manifest['incomplete_missing_original_count'] = len(missing)
    manifest['extra_files_require_rights_review'] = sum(1 for f in files if f['kind']=='extra')
    (pkg/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(f'Fertig: {sum(f["kind"]=="patch" for f in files)} Patches und {sum(f["kind"]=="extra" for f in files)} Zusatzdateien in {pkg}')
    if missing:
        print('NICHT RELEASEFERTIG: Fehlende Originale aufklaeren und danach neu bauen.')
    if any(f['kind']=='extra' for f in files):
        print('ACHTUNG: Die aufgenommenen Zusatzdateien auf Weitergaberechte pruefen, bevor etwas veroeffentlicht wird.')

def install(args):
    pkg = Path(args.package).resolve()
    clean = Path(args.clean).resolve()
    output = Path(args.output).resolve()
    doc = load_manifest(pkg/'manifest.json')
    if doc.get('incomplete_missing_original_count', 0):
        raise PatcherError('Dieses Paket ist unvollstaendig: siehe MISSING_ORIGINALS_REVIEW.txt. Nicht installieren oder veroeffentlichen.')
    if not clean.is_dir():
        raise PatcherError('Originalordner nicht gefunden.')
    if not doc['files']:
        raise PatcherError('Das Paket enthaelt keine Patches.')
    if output.exists():
        raise PatcherError('Zielordner existiert bereits. Bitte neuen leeren Zielpfad angeben.')
    if output.is_relative_to(clean) or clean.is_relative_to(output) or output.is_relative_to(pkg):
        raise PatcherError('Ausgabeordner muss getrennt von Originalen und Paket liegen.')
    # Full preflight, so mismatching game version fails before any output is produced.
    for entry in doc['files']:
        rp = rel_path(entry['path'])
        if entry['kind']=='patch':
            original = contained_file(clean, rp)
            patch = contained_file(pkg, patch_path(entry['patch']))
            if not original.is_file() or not patch.is_file():
                raise PatcherError(f'Datei fehlt: {entry["path"]}')
            check_hash(sha256(original),entry['original_sha256'],entry['path']+' (Original)')
        else:
            asset = contained_file(pkg, asset_path(entry['asset']))
            if not asset.is_file():
                raise PatcherError(f'Zusatzdatei fehlt: {entry["path"]}')
            check_hash(sha256(asset),entry['patched_sha256'],entry['path']+' (Zusatzdatei)')
    parent = output.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.reawakened_stage_',dir=parent))
    try:
        for entry in doc['files']:
            rp = rel_path(entry['path'])
            dst = contained_file(staging,rp)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if entry['kind']=='patch':
                src = contained_file(clean,rp)
                patch = contained_file(pkg,patch_path(entry['patch']))
                run_xdelta(args.xdelta,['-d','-f','-s',src,patch,dst])
            else:
                asset = contained_file(pkg,asset_path(entry['asset']))
                shutil.copyfile(asset, dst)
            check_hash(sha256(dst),entry['patched_sha256'],entry['path']+' (Mod)')
            print(f'Installiert und geprueft: {rp.as_posix()}')
        staging.rename(output)
        print(f'Erfolg: Lantern-Mod liegt in {output}')
    finally:
        if staging.exists():
            shutil.rmtree(staging)

def main():
    ap = argparse.ArgumentParser(description='Reawakened xdelta3-Build- und Installationswerkzeug')
    sub = ap.add_subparsers(dest='command',required=True)
    b = sub.add_parser('build',help='Aus eigenen Originalen und privatem Modbuild Patchdateien erzeugen')
    b.add_argument('--clean',required=True, help='Ordner mit unveraenderten dvdroot_ps4-Dateien')
    b.add_argument('--modified',required=True, help='Privater finaler Modordner mit dvdroot_ps4')
    b.add_argument('--package',required=True, help='Neuer leerer Ausgabeordner fuer Patches')
    b.add_argument('--xdelta',default='xdelta3', help='Pfad zu xdelta3.exe')
    b.add_argument('--approved-extras', help='TXT mit einzeln geprueften Zusatzdateien, eine dvdroot_ps4/... je Zeile')
    i = sub.add_parser('install',help='Patches auf die Originaldateien des Spielers anwenden')
    i.add_argument('--clean',required=True,help='Ordner mit unveraenderten dvdroot_ps4-Dateien')
    i.add_argument('--package',required=True,help='Release-Paket mit manifest.json und patches/')
    i.add_argument('--output',required=True,help='Neuer Ordner fuer fertige Lantern-Mod')
    i.add_argument('--xdelta',default='xdelta3',help='Pfad zu xdelta3.exe')
    args=ap.parse_args()
    try:
        if args.command=='build': build(args)
        else: install(args)
    except (PatcherError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'FEHLER: {exc}',file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
