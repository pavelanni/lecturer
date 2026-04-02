"""Load project configuration from lecturer.toml.

The config file lives in the course directory alongside the content/
and output/ subdirectories. All paths in the config are resolved
relative to the directory containing lecturer.toml.

Course directory layout:

    my-course/
        lecturer.toml
        content/
            lecture-01/
            lecture-02/
        output/

Config file format (TOML):

    [course]
    name = "My Course"
    content_dir = "content"
    output_dir = "output"
    voice_id = "your-elevenlabs-voice-id"
    lectures = ["lecture-01", "lecture-02"]
"""

import os
import sys
import tomllib
from pathlib import Path

CONFIG_FILENAME = "lecturer.toml"

_DEFAULTS = {
    "content_dir": "content",
    "output_dir": "output",
}


def _find_course_dir() -> Path:
    """Find the course directory.

    Checks (in order):
    1. LECTURER_COURSE_DIR environment variable
    2. Current working directory
    """
    env_dir = os.environ.get("LECTURER_COURSE_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return Path.cwd()


def load_config(course_dir: Path | str | None = None) -> dict:
    """Load and return the course configuration.

    Args:
        course_dir: Path to the course directory containing lecturer.toml.
                    If None, uses LECTURER_COURSE_DIR env var or cwd.

    Returns a dict with keys: name, content_dir, output_dir, lectures,
    voice_id. Paths are resolved to absolute Path objects.
    """
    if course_dir is not None:
        course_dir = Path(course_dir).resolve()
    else:
        course_dir = _find_course_dir()

    config_path = course_dir / CONFIG_FILENAME

    config = {
        "name": "",
        "content_dir": "",
        "output_dir": "",
        "lectures": [],
        "voice_id": "",
    }

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

    # Resolve relative paths against the course directory
    for key in ("content_dir", "output_dir"):
        p = Path(config[key])
        if not p.is_absolute():
            p = course_dir / p
        config[key] = p.resolve()

    return config


def get_content_dir(course_dir: Path | str | None = None) -> Path:
    """Return the resolved content directory path."""
    return load_config(course_dir)["content_dir"]


def get_output_dir(course_dir: Path | str | None = None) -> Path:
    """Return the resolved output directory path."""
    return load_config(course_dir)["output_dir"]


def list_lectures(
    course_dir: Path | str | None = None,
    *,
    content_dir: Path | str | None = None,
) -> list[Path]:
    """List lecture directories under the content dir.

    If lecturer.toml defines a ``lectures`` list, returns directories in
    that order.  Otherwise falls back to alphabetically sorted discovery
    of directories that contain a slides/ subdirectory or a
    narration_script.md file.

    Args:
        course_dir: Path to the course directory containing lecturer.toml.
        content_dir: Direct path to the content directory (skips config).
    """
    if content_dir is not None:
        content_dir = Path(content_dir).resolve()
        config = {"lectures": []}
    else:
        config = load_config(course_dir)
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
