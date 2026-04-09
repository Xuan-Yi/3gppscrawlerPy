from collections.abc import Iterable
from functools import total_ordering
from typing import Literal
import re
import logging

DocType = Literal["TR", "TS"]

logger = logging.getLogger(__name__)


@total_ordering
class TDocVersion:
    def __init__(self, version_str):
        self.raw = version_str
        self.major, self.minor = self._parse(version_str)

    def _parse(self, v):
        if isinstance(v, tuple):
            first, second = v[0], v[1]
        elif isinstance(v, str):
            m = re.match(r"([a-z]|\d)(\d+)", v, re.IGNORECASE)
            if m:
                first, second = m.groups()
            else:
                logger.warning("Unrecognized version string %r; treating as 0.0", v)
                first, second = '0', '0'
        else:
            logger.warning("Unexpected version type %r; treating as 0.0", type(v))
            first, second = '0', '0'

        major_val = int(first) if first.isdigit() else ord(first.lower()) + 100
        minor_val = int(second)
        return major_val, minor_val

    def __eq__(self, other):
        if not isinstance(other, TDocVersion):
            return NotImplemented
        return (self.major, self.minor) == (other.major, other.minor)

    def __lt__(self, other):
        if not isinstance(other, TDocVersion):
            return NotImplemented
        return (self.major, self.minor) < (other.major, other.minor)

    @property
    def tag(self) -> str:
        """Raw 3GPP version tag, e.g. 'j01'."""
        if isinstance(self.raw, tuple):
            return f"{self.raw[0]}{self.raw[1]}"
        return str(self.raw)

    def __str__(self) -> str:
        """Human-readable version string, e.g. '19.0.1'.

        3GPP encodes versions as XYZ where X is a letter (a=Rel-10, b=Rel-11, …)
        or digit (pre-Rel-10), Y is the technical version, and Z the editorial version.
        """
        if isinstance(self.raw, tuple):
            first, second = self.raw[0], self.raw[1]
        else:
            m = re.match(r"([a-z]|\d)(\d+)", str(self.raw), re.IGNORECASE)
            if not m:
                return str(self.raw)
            first, second = m.groups()

        release = int(first) if first.isdigit() else ord(first.lower()) - ord('a') + 10
        tech = int(second[0]) if second else 0
        edit = int(second[1:]) if len(second) > 1 else 0
        return f"{release}.{tech}.{edit}"


def find_latest_version(pattern: str, candidates: Iterable[str]) -> tuple | None:
    """
    Single-pass scan of `candidates` for strings matching `pattern`.
    Returns the raw regex-groups tuple for the highest TDocVersion found, or None.
    """
    best: tuple | None = None
    best_ver: "TDocVersion | None" = None
    for item in candidates:
        m = re.search(pattern, item, re.IGNORECASE)
        if m:
            groups = m.groups()
            ver = TDocVersion(groups)
            if best_ver is None or ver > best_ver:
                best, best_ver = groups, ver
    return best


class TDoc:
    def __init__(self, number, doc_type: DocType = "TR"):
        self.number = number
        self.doc_type = doc_type
        self.series = f"{number.split('.')[0]}_series"
        self.clean_number = number.replace('.', '')

    def get_filename_pattern(self):
        return rf"{self.clean_number}-([a-z]|\d)(\d+)\.(?:zip|docx?|pdf)"

    def format_filename(self, version_tuple):
        return f"{self.clean_number}-{version_tuple[0]}{version_tuple[1]}.zip"
