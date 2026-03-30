"""Load project configuration from lecturer.toml.

Looks for lecturer.toml in the current working directory or the project
root (directory containing pyproject.toml). Falls back to ./content and
./output if no config file is found.

Config file format (TOML):

    [course]
    name = "My Course"
    content_dir = "/absolute/path/to/content"
    output_dir = "/absolute/path/to/output"
    lectures = ["lecture-01", "lecture-02", "lecture-03"]
"""

import tomllib
from pathlib import Path

CONFIG_FILENAME = "lecturer.toml"

# Defaults (relative to project root)
_DEFAULTS = {
    "content_dir": "content",
    "output_dir": "output",
}


def _find_project_root() -> Path:
    """Walk up from cwd to find the directory containing pyproject.toml."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return current


def load_config() -> dict:
    """Load and return the course configuration.

    Returns a dict with keys: name, content_dir, output_dir.
    Paths are resolved to absolute Path objects.
    """
    root = _find_project_root()
    # Check cwd first (for Docker: lecturer.toml in /course, code in /app)
    cwd_config = Path.cwd() / CONFIG_FILENAME
    config_path = cwd_config if cwd_config.exists() else root / CONFIG_FILENAME

    config = {"name": "", "content_dir": "", "output_dir": "", "lectures": [],
              "voice_id": ""}

    if config_path.exists():
        with open(config_path, "rb") as f:
            raw = tomllib.load(f)
        course = raw.get("course", {})
        config["name"] = course.get("name", "")
        config["content_dir"] = course.get("content_dir", _DEFAULTS["content_dir"])
        config["output_dir"] = course.get("output_dir", _DEFAULTS["output_dir"])
        config["lectures"] = course.get("lectures", [])
        config["voice_id"] = course.get("voice_id", "")
    else:
        config["content_dir"] = _DEFAULTS["content_dir"]
        config["output_dir"] = _DEFAULTS["output_dir"]

    # Resolve relative paths against project root
    for key in ("content_dir", "output_dir"):
        p = Path(config[key])
        if not p.is_absolute():
            p = root / p
        config[key] = p.resolve()

    return config


def get_content_dir() -> Path:
    """Return the resolved content directory path."""
    return load_config()["content_dir"]


def get_output_dir() -> Path:
    """Return the resolved output directory path."""
    return load_config()["output_dir"]


def list_lectures(content_dir: Path | None = None) -> list[Path]:
    """List lecture directories under the content dir.

    If lecturer.toml defines a ``lectures`` list, returns directories in
    that order.  Otherwise falls back to alphabetically sorted discovery
    of directories that contain a slides/ subdirectory or a
    narration_script.md file.
    """
    config = load_config()
    if content_dir is None:
        content_dir = config["content_dir"]

    if not content_dir.is_dir():
        return []

    configured = config.get("lectures", [])
    if configured:
        lectures = []
        for name in configured:
            path = content_dir / name
            if path.is_dir():
                lectures.append(path)
        return lectures

    # Fallback: auto-discover
    lectures = []
    for entry in sorted(content_dir.iterdir()):
        if not entry.is_dir():
            continue
        if (entry / "slides").is_dir() or (entry / "narration_script.md").exists():
            lectures.append(entry)

    return lectures
