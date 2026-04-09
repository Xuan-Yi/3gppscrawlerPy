"""
Command-line interface to check and optionally update 3GPP Technical Reports (TRs).

Pipeline (when not --check-only):
  Phase 1 — Check all TRs concurrently        (async, rate-limited)
  Phase 2 — Download all outdated TRs         (async, rate-limited, parallel progress bars)
  Phase 3 — Extract zips                      (thread pool)
  Phase 4 — Convert to PDF (--export-pdf)     (thread pool)
"""

import argparse
import asyncio
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich import box

from tools import config
from tools.network import AsyncNetworkClient
from tools.manager import AsyncTDocManager

console = Console()


# --------------------------------------------------------------------------- reporting

def _print_check_report(results: list[dict]) -> None:
    """Render a rich table summarising Phase 1 results."""
    if not results:
        return

    table = Table(
        title="TDoc Status Report",
        box=box.ROUNDED,
        show_lines=False,
        highlight=True,
    )
    table.add_column("Type",    style="magenta", no_wrap=True)
    table.add_column("Number",  style="cyan bold",  no_wrap=True)
    table.add_column("Status",  no_wrap=True)
    table.add_column("Local",   style="dim",  no_wrap=True)
    table.add_column("Latest",  no_wrap=True)

    for r in results:
        tr = r["tr"]
        doc_type = r["doc_type"]
        if r["status"] == "error":
            table.add_row(doc_type, tr, "[red]ERROR[/red]", "—", r.get("error", ""))
        elif r["status"] == "not_found":
            table.add_row(doc_type, tr, "[yellow]NOT FOUND[/yellow]", "—", "—")
        elif r["update_available"]:
            table.add_row(
                doc_type,
                tr,
                "[green]UPDATE[/green]",
                str(r["local_version"]) if r["local_version"] else "—",
                f"[bold green]{r['latest_version']}[/bold green]",
            )
        else:
            table.add_row(doc_type, tr, "[blue]UP TO DATE[/blue]", str(r["local_version"]), "—")

    console.print(table)


def _phase(label: str) -> None:
    console.rule(f"[bold]{label}[/bold]")


def _collect_phase_failures(
    items: list[dict],
    results: list,
    label: str,
    failures: list[str],
    successes: list[dict] | None = None,
) -> None:
    """Process asyncio.gather results, log errors, and populate failures/successes lists."""
    for info, result in zip(items, results):
        label_doc = f"{info['doc_type']} {info['tr']}"
        if isinstance(result, Exception):
            logging.error("%s failed for %s: %s", label, label_doc, result)
            failures.append(label_doc)
        elif result is False:
            failures.append(label_doc)
        elif successes is not None:
            successes.append(info)


# --------------------------------------------------------------------------- pipeline

async def _run(args: argparse.Namespace) -> list[str]:
    """Execute the full pipeline. Returns a list of failed TR/TS identifiers."""
    docs: list[tuple[str, str]] = (
        [(n, "TR") for n in (args.tr or [])] +
        [(n, "TS") for n in (args.ts or [])]
    )

    failures: list[str] = []

    async with AsyncNetworkClient() as network:
        manager = AsyncTDocManager(network)

        # ── Phase 1: Check all TRs/TSs ───────────────────────────────────────
        _phase(f"Phase 1 — Checking {len(docs)} document(s)")
        raw_results = await asyncio.gather(
            *[manager.check_tr(number, doc_type) for number, doc_type in docs],
            return_exceptions=True,
        )

        all_infos: list[dict] = []
        for (number, doc_type), result in zip(docs, raw_results):
            label = f"{doc_type} {number}"
            if isinstance(result, Exception):
                logging.error("%s: unexpected error — %s", label, result)
                failures.append(label)
            else:
                all_infos.append(result)
                if result["status"] in ("not_found", "error"):
                    failures.append(label)

        _print_check_report(all_infos)

        if args.check_only:
            return failures

        # ── Phase 2: Download outdated documents ──────────────────────────────
        to_download = [r for r in all_infos if r["status"] == "found" and r["update_available"]]
        _phase(f"Phase 2 — Downloading {len(to_download)} document(s)")

        if to_download:
            print()  # breathing room above tqdm bars
            dl_results = await asyncio.gather(
                *[manager.download_tr(info, bar_position=i)
                  for i, info in enumerate(to_download)],
                return_exceptions=True,
            )
            print()  # breathing room below tqdm bars

            downloaded: list[dict] = []
            _collect_phase_failures(to_download, dl_results, "Download", failures, downloaded)
        else:
            logging.info("Nothing to download.")
            downloaded = []

        # ── Phase 3: Extract ──────────────────────────────────────────────────
        if args.force_extract or args.export_pdf:
            to_extract = [r for r in all_infos if r["status"] == "found"]
        else:
            to_extract = downloaded

        _phase(f"Phase 3 — Extracting {len(to_extract)} document(s)")

        if to_extract:
            ex_results = await asyncio.gather(
                *[manager.run_in_executor(
                    manager.extract_tr, info,
                    args.force_extract, args.no_extract, args.export_pdf,
                  ) for info in to_extract],
                return_exceptions=True,
            )
            _collect_phase_failures(to_extract, ex_results, "Extraction", failures)
        else:
            logging.info("Nothing to extract.")

        # ── Phase 4: PDF conversion ───────────────────────────────────────────
        if args.export_pdf:
            to_convert = [r for r in all_infos if r["status"] == "found"]
            _phase(f"Phase 4 — Converting {len(to_convert)} document(s) to PDF")
            cv_results = await asyncio.gather(
                *[manager.run_in_executor(manager.convert_tr, info)
                  for info in to_convert],
                return_exceptions=True,
            )
            _collect_phase_failures(to_convert, cv_results, "PDF conversion", failures)

    return failures


# --------------------------------------------------------------------------- entry point

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check and optionally update 3GPP Technical Reports (TR) and Technical Specifications (TS).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-t", "--tr", metavar="TR", nargs="+", action="extend",
        help="TR numbers to process (e.g. -t 38.811 38.821). Repeatable.",
    )
    parser.add_argument(
        "-s", "--ts", metavar="TS", nargs="+", action="extend",
        help="TS numbers to process (e.g. -s 23.501 23.502). Repeatable.",
    )
    parser.add_argument("--check-only", action="store_true",
                        help="Report status only; do not download or extract.")
    parser.add_argument("--export-pdf", action="store_true",
                        help="Convert extracted .doc/.docx to PDF after processing.")
    parser.add_argument("--no-extract", action="store_true",
                        help="Skip zip extraction (overridden by --export-pdf).")
    parser.add_argument("--force-extract", action="store_true",
                        help="Re-extract even if the document is already up to date.")
    parser.add_argument("--workers", type=int, default=config.MAX_WORKERS,
                        help=f"Thread-pool size for extract/convert phases (default: {config.MAX_WORKERS}).")

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    verbosity.add_argument("--quiet", action="store_true", help="Suppress informational output.")

    args = parser.parse_args()

    if not args.tr and not args.ts:
        parser.error("Specify at least one document: --tr <number> or --ts <number>")

    level = logging.DEBUG if args.verbose else (logging.WARNING if args.quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )

    failures = asyncio.run(_run(args))

    if failures:
        unique = list(dict.fromkeys(failures))
        logging.warning("Failed TRs: %s", ", ".join(unique))
        sys.exit(1)


if __name__ == "__main__":
    main()
