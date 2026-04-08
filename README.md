# 3GPP TDoc Scrawler

A command-line tool to check and optionally update 3GPP Technical Reports (TRs). It queries the 3GPP FTP archive, compares remote versions with local files, and downloads/extracts updates concurrently.

## Features

- **Parallel checks**: All TR status checks run concurrently (rate-limited to respect the 3GPP server).
- **Parallel downloads**: Outdated TRs download simultaneously with per-file progress bars.
- **Check for updates**: Compares local and remote versions of 3GPP TRs.
- **Selective update**: Download and extract only if newer versions exist.
- **Flexible selection**: Process specific TRs or use a configurable default list.
- **Dry run**: Check-only mode with a rich status table — no downloads triggered.
- **Extraction control**: Optionally skip or force extraction.
- **PDF Export**: Parallel conversion of extracted Word documents to PDF via Word COM.
- **Rich logging**: Colored log output and formatted status tables via `rich`.
- **TOML configuration**: All settings (timeouts, concurrency, TR list) in `config.toml`.

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
base_url        = "https://www.3gpp.org/ftp/Specs/archive/"
timeout_page    = 15      # seconds for archive page fetch
timeout_download = 30     # seconds between chunks during download
retry_attempts  = 3
retry_backoff   = 1.0
max_concurrent  = 3       # max simultaneous connections to 3GPP server

[storage]
local_folder    = "./3gpp_trs"

[processing]
max_workers     = 4       # thread-pool size for extract/convert phases
max_word_instances = 2    # parallel Word COM instances for PDF conversion

[trs]
default_list = ["38.811", "38.821", ...]
```

## Usage

```sh
uv run cli.py [options]
```

### Options

| Option | Description |
|--------|-------------|
| `-t`, `--tr <TR>` | TR numbers to process (e.g. `-t 38.811 38.821`). Repeatable. Defaults to `config.toml` list. |
| `--check-only` | Report status only; do not download or extract. |
| `--export-pdf` | Convert extracted `.doc`/`.docx` to PDF after processing. |
| `--no-extract` | Skip zip extraction (overridden by `--export-pdf`). |
| `--force-extract` | Re-extract even if the TR is already up to date. |
| `--workers N` | Thread-pool size for extract/convert phases (default: 4). |
| `--verbose` | Enable debug logging. |
| `--quiet` | Suppress informational output. |

### Examples

```sh
# Check default TRs — shows a rich status table, no downloads
uv run cli.py --check-only

# Update a specific TR and export to PDF
uv run cli.py -t 38.811 --export-pdf

# Force re-extract a specific TR
uv run cli.py -t 38.811 --force-extract

# Update specific TRs without extracting zips
uv run cli.py -t 38.811 38.821 --no-extract

# Run with more parallel workers
uv run cli.py --workers 7
```

## How It Works

The pipeline runs in four phases:

1. **Phase 1 — Check** (async, rate-limited): All TRs are queried concurrently. Results are displayed as a rich table showing local version, remote version, and update status.
2. **Phase 2 — Download** (async, rate-limited): Outdated TRs are downloaded in parallel with per-file progress bars.
3. **Phase 3 — Extract** (thread pool): Downloaded zips are extracted concurrently. Zip files are deleted after successful extraction.
4. **Phase 4 — Convert** (thread pool, `--export-pdf` only): Extracted Word documents are converted to PDF in parallel using Word COM automation, with up to `max_word_instances` simultaneous Word processes.

## Default TR List

Configured in `config.toml` under `[trs] default_list`:

```
38.811, 38.821, 38.863, 38.820, 38.921, 36.942, 38.814, 38.815, 38.901, 38.913
```

## Dependencies

- Python 3.12+
- `aiohttp` — async HTTP
- `beautifulsoup4` — HTML parsing
- `tqdm` — download progress bars
- `rich` — logging and status tables
- `pywin32` — Word COM automation for PDF export (Windows only)

## Todos
1. Extend to TS
2. Extend to TDocs with messy inputs
3. PDF diff viewer (PyMuPDF + difflib)
4. GUI reader (Rust + TypeScript/Tauri)
