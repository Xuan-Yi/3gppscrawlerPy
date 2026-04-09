# 3GPP TDoc Scrawler

A command-line tool to check and optionally update 3GPP Technical Reports (TRs) and Technical Specifications (TSs). It queries the 3GPP FTP archive, compares remote versions with local files, and downloads/extracts updates concurrently.

## Features

- Concurrent check, download, extract, and PDF conversion for any mix of TRs and TSs
- Dry-run mode (`--check-only`) with a rich status table
- Separate output subfolders (`3gpp_trs/TR/`, `3gpp_trs/TS/`)
- Parallel Word COM PDF export; skip/force extraction flags
- TOML configuration; colored logging via `rich`

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management. Requires **Python 3.12+**.

1. **Install uv** (if not already installed):
   ```sh
   scoop install uv
   ```
   *(For other platforms, see [uv installation](https://github.com/astral-sh/uv#installation))*

2. **Sync dependencies**:
   ```sh
   uv sync
   ```

## Configuration

All settings live in `config.toml` at the project root:

```toml
[network]
base_url         = "https://www.3gpp.org/ftp/Specs/archive/"
timeout_page     = 15      # seconds for archive page fetch
timeout_download = 30      # seconds between chunks during download
retry_attempts   = 3
retry_backoff    = 1.0
max_concurrent   = 3       # max simultaneous connections to 3GPP server

[storage]
tr_folder        = "./3gpp_docs/TR"
ts_folder        = "./3gpp_docs/TS"

[processing]
max_workers      = 4       # thread-pool size for extract/convert phases
max_word_instances = 2     # parallel Word COM instances for PDF conversion
```

## Usage

```sh
uv run cli.py [options]
```

At least one of `--tr` or `--ts` must be specified.

### Options

| Option | Description |
|--------|-------------|
| `-t`, `--tr <TR>` | TR numbers to process (e.g. `-t 38.811 38.821`). Repeatable. |
| `-s`, `--ts <TS>` | TS numbers to process (e.g. `-s 23.501 23.502`). Repeatable. |
| `--check-only` | Report status only; do not download or extract. |
| `--export-pdf` | Convert extracted `.doc`/`.docx` to PDF after processing. |
| `--no-extract` | Skip zip extraction (overridden by `--export-pdf`). |
| `--force-extract` | Re-extract even if the document is already up to date. |
| `--workers N` | Thread-pool size for extract/convert phases (default: 4). |
| `--verbose` | Enable debug logging. |
| `--quiet` | Suppress informational output. |

### Examples

```sh
# Check a TR and a TS — shows a rich status table (including PDF status)
uv run cli.py -t 38.811 -s 23.501 --check-only

# Update a specific TR and export to PDF (skips if PDF already exists)
uv run cli.py -t 38.811 --export-pdf
```

## How It Works

The pipeline runs in four phases:

1. **Phase 1 — Check** (async, rate-limited): All documents are queried concurrently. Results are displayed as a rich table showing type, local version, remote version, PDF status, and update status.
2. **Phase 2 — Download** (async, rate-limited): Outdated documents are downloaded in parallel with per-file progress bars.
3. **Phase 3 — Extract** (thread pool): Downloaded zips are extracted concurrently into their respective subfolders. Zip files are deleted after successful extraction.
4. **Phase 4 — Convert** (thread pool, `--export-pdf` only): Extracted Word documents are converted to PDF in parallel using isolated Word COM instances. The source documents are **preserved** after conversion. Redundant conversions are skipped if a PDF with the matching version tag already exists.

## Output Layout

```
3gpp_trs/
├── TR/
│   ├── 38811-j00.doc
│   └── 38811-j00.pdf
└── TS/
    ├── 23501-k10.doc
    └── 23501-k10.pdf
```

## Dependencies

- Python 3.12+
- `aiohttp` — async HTTP
- `beautifulsoup4` — HTML parsing
- `tqdm` — download progress bars
- `rich` — logging and status tables
- `pywin32` — Word COM automation for PDF export (Windows only)

## Todos
1. Extend to TDocs with messy inputs
2. GUI reader (Rust + TypeScript/Tauri)
3. PDF diff viewer (PyMuPDF + difflib)

