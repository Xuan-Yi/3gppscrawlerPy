from functools import total_ordering
import re

@total_ordering
class TRVersion:
    def __init__(self, version_str):
        self.raw = version_str
        self.major, self.minor = self._parse(version_str)

    def _parse(self, v):
        # v is likely a tuple or string.
        # The original code handled tuples ('f', '20') or ('1', '0')
        # Let's standardize on the tuple or string.
        if isinstance(v, tuple):
             first = v[0]
             second = v[1]
        elif isinstance(v, str):
            # If string like "f20" or "100"
            # It's actually tricky because the regex in original code split it:
            # ([a-z]|\d)(\d+)
            m = re.match(r"([a-z]|\d)(\d+)", v, re.IGNORECASE)
            if m:
                first, second = m.groups()
            else:
                first, second = '0', '0' # Fallback
        else:
             first, second = '0', '0'

        # Logic from original version_key
        # Digits are sorted before letters.
        # But wait, original code:
        # first = int(v[0]) if v[0].isdigit() else ord(v[0].lower()) + 100
        # If v[0] is digit (e.g. '1'), it becomes int(1).
        # If v[0] is letter (e.g. 'f'), it becomes ord('f') + 100.
        # So '1' (1) < 'f' (102+100=202).
        # So digits come BEFORE letters.
        
        major_val = int(first) if first.isdigit() else ord(first.lower()) + 100
        minor_val = int(second)
        return major_val, minor_val

    def __eq__(self, other):
        if not isinstance(other, TRVersion):
            return NotImplemented
        return (self.major, self.minor) == (other.major, other.minor)

    def __lt__(self, other):
        if not isinstance(other, TRVersion):
            return NotImplemented
        return (self.major, self.minor) < (other.major, other.minor)

    def __str__(self):
        # We need to reconstruct the original representation if possible,
        # but since we transformed it, we might rely on the raw value passed in if accessible.
        # For now, let's assume raw is kept or we don't strictly need to reconstruct it 
        # exactly unless we store the parts.
        if isinstance(self.raw, tuple):
            return f"{self.raw[0]}{self.raw[1]}"
        return str(self.raw)

class TR:
    def __init__(self, number):
        self.number = number
        self.series = f"{number[:2]}_series"
        # Sanitize for filename usage
        self.clean_number = number.replace('.', '')

    def get_filename_pattern(self):
        # pattern = rf"{tr_number.replace('.', '')}-([a-z]|\d)(\d+)\.zip"
        # Updated to match zip, doc, docx, pdf
        return rf"{self.clean_number}-([a-z]|\d)(\d+)\.(?:zip|docx?|pdf)"
    
    def format_filename(self, version_tuple):
        return f"{self.clean_number}-{version_tuple[0]}{version_tuple[1]}.zip"
