# 3GPP TDoc Scrawler

A command-line tool to check and optionally update 3GPP Technical Reports (TRs). This script queries remote metadata for specified TR numbers, compares them with local versions, and downloads/extracts updates if available.

## Features

- **Check for updates**: Compares local and remote versions of 3GPP TRs.
- **Selective update**: Download and extract only if newer versions exist.
- **Flexible selection**: Process specific TRs or use a default list.
- **Dry run**: Check-only mode to report updates without downloading.
- **Extraction control**: Optionally skip or force extraction.
- **PDF Export**: Convert extracted documents to PDF format.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

1. **Install uv** (if not already installed):
   ```sh
   scoop install uv
   ```
   *(For other platforms, see [uv installation](https://github.com/astral-sh/uv#installation))*

2. **Sync dependencies**:
   ```sh
   uv sync
   ```

## Usage

You can run the CLI tool using `uv run`:

```sh
uv run cli.py [options]
```

### Options

- `-t`, `--tr` `<TR>`: Specify one or more TR numbers (e.g., `-t 38.811 38.821`). Can be repeated. If omitted, uses a default list.
- `--check-only`: Only check and report status; do not download or extract updates.
- `--export-pdf`: Export the extracted `.doc`/`.docx` files to PDF format.
- `--no-extract`: Do not extract downloaded ZIP files (useful when you want only the ZIPs).
- `--force-extract`: Force extraction even if the file is already up to date.

### Examples

- **Check default TRs without downloading:**
    ```sh
    uv run cli.py --check-only
    ```

- **Update a specific TR and export to PDF:**
    ```sh
    uv run cli.py -t 38.811 --export-pdf
    ```

- **Force extract a specific TR:**
    ```sh
    uv run cli.py -t 38.811 --force-extract
    ```

- **Update specific TRs without extracting:**
    ```sh
    uv run cli.py -t 38.811 38.821 --no-extract
    ```

## How It Works

The CLI uses `tools.manager.TRManager` to coordinate the following steps for each TR:

1. **Check TR**: Fetches remote metadata and compares it with local files to determine if an update is available.
2. **Download**: If an update is found (and not in `--check-only` mode), it downloads the latest ZIP file.
3. **Extract**: Automatically extracts the ZIP file unless `--no-extract` is specified.
4. **Export PDF**: If `--export-pdf` is enabled, it converts the extracted Word documents to PDF.

## Default TR List

If no TRs are specified, the following are checked by default:

```
38.811, 38.821, 38.863, 38.820, 38.921, 36.942, 38.814, 38.815, 38.901, 38.913
```

## Dependencies

- Python 3.x
- Required packages (see `pyproject.toml` or `uv.lock`)
- `tools` package (provides `TRManager`, `config`, etc.)
- 
## Todos
1. Extend to TS
2. Extend to TDocs with messy inputs