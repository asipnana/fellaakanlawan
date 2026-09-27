"""
repo_ingest.py — Repo Ripple (Person A)

Validates a local filesystem path before handing it to the analyzer.
This tool is local-only by design: no git URLs, no cloning, no network.
"""

import os
import re

# Patterns that indicate a URL or remote ref — all rejected with a clear error.
_URL_PATTERNS = re.compile(
    r"^(https?://|git@|git://|ssh://|ftp://|ftps://)"
    r"|\.git$",
    re.IGNORECASE,
)


class RepoIngestionError(ValueError):
    """Raised when the supplied path fails validation."""


def get_validated_repo_path(path: str) -> str:
    """Validate *path* as a usable local repository root and return it.

    Rules
    -----
    - Must be a plain local filesystem path (no URL schemes, no .git suffix).
    - The path must exist on disk.
    - The path must be a directory (not a file or symlink to a file).
    - The directory must be non-empty (contain at least one entry).

    Parameters
    ----------
    path : str
        The filesystem path supplied at runtime (e.g. from a CLI argument or
        a config value).

    Returns
    -------
    str
        The absolute, normalised version of *path* — safe to pass directly to
        the analyzer scripts.

    Raises
    ------
    RepoIngestionError
        With a descriptive message for any of the failure cases above.
    """
    if not isinstance(path, str) or not path.strip():
        raise RepoIngestionError("Repo path must be a non-empty string.")

    path = path.strip()

    # Reject anything that looks like a URL or remote git reference.
    if _URL_PATTERNS.search(path):
        raise RepoIngestionError(
            f"Remote paths and git URLs are not supported — this tool is "
            f"local-only by design.\n"
            f"  Received: {path!r}\n"
            f"  Provide a local filesystem path instead (e.g. /home/user/myrepo)."
        )

    abs_path = os.path.abspath(path)

    if not os.path.exists(abs_path):
        raise RepoIngestionError(
            f"Path does not exist on disk: {abs_path!r}"
        )

    if not os.path.isdir(abs_path):
        raise RepoIngestionError(
            f"Path exists but is not a directory: {abs_path!r}"
        )

    entries = os.listdir(abs_path)
    if not entries:
        raise RepoIngestionError(
            f"Directory is empty — nothing to analyze: {abs_path!r}"
        )

    return abs_path
