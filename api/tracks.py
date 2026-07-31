"""Base-track catalog, discovered from the files in assets/tracks/.

The BPM is a property of the audio, not of the deployment, so it is parsed
from the filename (``*_<bpm>bpm.mp3``) instead of living in an env var - the
tempo the frontend schedules around and the track it loops can never disagree.
Adding a soundtrack is dropping a correctly named mp3 into assets/tracks/.
"""

import logging
import random
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

TRACKS_DIR = Path(__file__).parent.parent / "assets" / "tracks"

_BPM_PATTERN = re.compile(r"_(\d+)bpm\.mp3$")


@dataclass(frozen=True)
class Track:
    """One base instrumental the battle can run over."""

    filename: str
    bpm: int

    @property
    def url(self) -> str:
        return f"/static/tracks/{self.filename}"


def discover_tracks(tracks_dir: Path = TRACKS_DIR) -> list[Track]:
    """Build the catalog from the mp3s on disk, sorted by filename."""
    tracks = []
    if tracks_dir.exists():
        for path in sorted(tracks_dir.glob("*.mp3")):
            match = _BPM_PATTERN.search(path.name)
            if match:
                tracks.append(Track(filename=path.name, bpm=int(match.group(1))))
            else:
                logger.warning(
                    "Ignoring track without a *_<bpm>bpm.mp3 name: %s", path.name
                )
    return tracks


TRACKS = discover_tracks()


def choose_track() -> Track:
    """Pick the base track for a new session (random once there are several)."""
    if not TRACKS:
        raise RuntimeError(
            f"No base tracks found in {TRACKS_DIR} (expected *_<bpm>bpm.mp3)"
        )
    return random.choice(TRACKS)
