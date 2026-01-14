# 3GPP TR Scrawler CLI

A command-line tool to check and optionally update 3GPP Technical Reports (TRs). This script queries remote metadata for specified TR numbers, compares them with local versions, and downloads/extracts updates if available.

## Features

- **Check for updates**: Compares local and remote versions of 3GPP TRs.
- **Selective update**: Download and extract only if newer versions exist.
- **Flexible selection**: Process specific TRs or use a default list.
- **Dry run**: Check-only mode to report updates without downloading.
- **Extraction control**: Optionally skip extraction after download.

## Usage

```sh
python cli.py [options]
```

### Options

- `-t`, `--tr` `<TR>`: Specify one or more TR numbers (e.g., `-t 38.811 38.821`). Can be repeated. If omitted, uses a default list.
- `--check-only`: Only check and report status; do not download or extract updates.
- `--no-extract`: Do not extract downloaded ZIP files (useful when you want only the ZIPs).

### Examples

- **Check default TRs without downloading:**
    ```sh
    python cli.py --check-only
    ```

- **Check specific TRs without downloading:**
    ```sh
    python cli.py -t 38.811 38.821 --check-only
    ```

- **Update a specific TR and extract the downloaded ZIP:**
    ```sh
    python cli.py -t 38.811
    ```

- **Update a specific TR without extracting:**
    ```sh
    python cli.py -t 38.811 --no-extract
    ```

## How It Works

For each TR number:

1. **Fetch remote version** using `tools.scrawler.get_latest_tr_version(tr)`.
2. **Check local version** using `tools.scrawler.get_local_tr_version(tr)`.
3. **Compare versions** with `tools.scrawler.version_key`.
4. **If update available**:
        - In check-only mode: report update.
        - Otherwise: download with `tools.scrawler.download_tr` and extract with `tools.scrawler.extract_zip_file` (unless `--no-extract` is set).
5. **If up to date**: print current version.

## Dependencies

- Python 3.x
- `tools.scrawler` module (must provide required functions)

## Default TR List

If no TRs are specified, the following are checked by default:

```
38.811, 38.821, 38.863, 38.820, 38.921, 36.942, 38.814, 38.815, 38.901, 38.913
```
