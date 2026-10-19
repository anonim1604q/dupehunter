# dupehunter

Find duplicate files fast, and clean them up **safely**. Pure Python standard library: no dependencies, works on Linux, macOS and Windows.

[English](README.md) | [Русский](README.ru.md)

## Why

Photos, downloads and backups quietly fill your disk with copies. `dupehunter` finds them without reading every file in full, and never touches anything unless you say so.

## Features

- **Fast 3-stage search**: group by size, then hash the first 64 KiB, then hash the whole file only for real candidates (BLAKE2b, multithreaded).
- **Safe by default**: read-only. Actions are a *dry run* until you pass `--apply`.
- **Re-verifies bytes** before every delete/move/hardlink, so a file changed after the scan is skipped.
- **Smart handling**: symlinks are ignored, hardlinks are not reported as duplicates, empty files are skipped.
- **Three actions**: `--delete`, `--move-to DIR`, `--hardlink` (atomic swap, a file is never missing).
- **Keep policy**: `--keep oldest|newest|shortest` (shortest path).
- **Automation-ready**: `--json` output, `--fail-on-dupes` exit code for CI.

## Install

```bash
pipx install git+https://github.com/<your-username>/dupehunter
# or run without installing:
git clone https://github.com/<your-username>/dupehunter && cd dupehunter
python -m dupehunter --help
```

Requires Python 3.9+.

## Usage

```bash
# Report only (nothing is changed)
dupehunter ~/Pictures ~/Downloads

# Only files >= 5 MiB, skip some folders
dupehunter ~/Downloads -m 5M -x node_modules -x '*.tmp'

# Preview, then actually move extra copies to a folder
dupehunter ~/Pictures --move-to ~/dupes --keep oldest
dupehunter ~/Pictures --move-to ~/dupes --keep oldest --apply

# Replace copies with hardlinks to save space but keep every path working
dupehunter ~/backup --hardlink --apply

# JSON for scripts
dupehunter ~/data --json > dupes.json

# CI check: fail if the repo has duplicate assets
dupehunter ./assets --fail-on-dupes -q
```

Example output:

```
[1] 3 copies x 4.2 MiB  (wasted 8.4 MiB)
  keep  /home/me/Pictures/trip/IMG_001.jpg
        /home/me/Pictures/backup/IMG_001.jpg
        /home/me/Downloads/IMG_001 (1).jpg

Scanned 12804 files: 41 duplicate groups, 57 redundant files, 1.3 GiB reclaimable.
```

## Options

| Option | Description |
|---|---|
| `-m, --min-size SIZE` | Ignore files smaller than SIZE (`10K`, `5M`, `1G`) |
| `-x, --exclude GLOB` | Skip matching files/dirs (repeatable) |
| `--hidden` | Include hidden files and directories |
| `--keep POLICY` | `oldest` (default), `newest`, `shortest` |
| `--delete` / `--move-to DIR` / `--hardlink` | Action for redundant copies (mutually exclusive) |
| `--apply` | Really perform the action (default: dry run) |
| `-y, --yes` | Skip the confirmation prompt |
| `--json` | Machine-readable report |
| `--fail-on-dupes` | Exit code 1 if duplicates found |
| `-j, --jobs N` | Hashing threads |
| `-q, --quiet` | No progress output |

## Development

```bash
python -m unittest discover -s tests -v
```

## License

MIT
