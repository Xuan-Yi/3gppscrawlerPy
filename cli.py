"""
Command-line interface to check and optionally update 3GPP Technical Reports (TRs).
Refactored to be extensible using tools.manager.
"""

import argparse
from tools import config
from tools.manager import TRManager


def main():
    parser = argparse.ArgumentParser(description="Check and optionally update 3GPP TRs")
    parser.add_argument(
        "-t",
        "--tr",
        metavar="TR",
        nargs="+",
        action="extend",
        help="Specify one or more TR numbers (e.g., -t 38.811 38.821). Can be repeated.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check and report status; do not download or extract updates.",
    )
    parser.add_argument(
        "--export-pdf",
        action="store_true",
        help="Export the specified .doc/.docx files to PDF format after extraction.",
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Do not extract downloaded zip files (useful with --check-only disabled).",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Force extraction even if the file is up to date.",
    )
    args = parser.parse_args()

    # Determine list of TRs
    if args.tr:
        tr_list = args.tr
    else:
        tr_list = config.DEFAULT_TR_LIST
        print(f"No TRs specified; using default list: {', '.join(tr_list)}")

    manager = TRManager()

    for tr_number in tr_list:
        print(f"Checking {tr_number}...")

        info: dict = manager.check_tr(tr_number)

        if info["status"] == "not_found":
            print(f"No remote info found for {tr_number}")
            print("")
            continue

        # Determine status message
        latest_ver = info["latest_version"]
        local_ver = info["local_version"]

        if info["update_available"]:
            print(f"Update available: {tr_number} ({local_ver} -> {latest_ver})")
        else:
            print(f"{tr_number} is up to date (version {local_ver})")

        # Action phase
        if args.check_only:
            if info["update_available"]:
                print("Check-only mode: skipping download/extract.")
        else:
            # Update / Extract / Export
            manager.update_tr(info, force_extract=args.force_extract, no_extract=args.no_extract, export_pdf=args.export_pdf)

        print("")


if __name__ == "__main__":
    main()
