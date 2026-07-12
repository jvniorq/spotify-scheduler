from __future__ import annotations

import random
from collections import deque
from collections.abc import Iterable


def _primary_artist(track: dict[str, object]) -> str:
    artists = track.get("artists") or []
    if not isinstance(artists, list) or not artists:
        return ""
    first = artists[0]
    if isinstance(first, dict):
        return str(first.get("id") or first.get("name") or "")
    return str(first)


def build_random_queue(
    tracks: Iterable[dict[str, object]],
    *,
    recent_uris: set[str] | None = None,
    max_tracks: int = 100,
    avoid_same_artist: bool = True,
    rng: random.Random | None = None,
) -> list[dict[str, object]]:
    """Return a shuffled queue with simple anti-repetition rules.

    The function:
    - removes local/unavailable tracks,
    - removes duplicate URIs,
    - excludes recently played tracks,
    - tries to avoid consecutive primary artists,
    - limits the result to ``max_tracks``.
    """

    recent_uris = recent_uris or set()
    rng = rng or random.SystemRandom()

    unique: dict[str, dict[str, object]] = {}
    for track in tracks:
        uri = str(track.get("uri") or "")
        if not uri or ":local:" in uri or not track.get("is_playable", True):
            continue
        unique.setdefault(uri, track)

    eligible = [track for uri, track in unique.items() if uri not in recent_uris]
    rng.shuffle(eligible)

    pool = deque(eligible)
    result: list[dict[str, object]] = []
    previous_artist = ""

    while pool and len(result) < max_tracks:
        selected_index = 0

        if avoid_same_artist and previous_artist:
            for index, candidate in enumerate(pool):
                artist = _primary_artist(candidate)
                if not artist or artist != previous_artist:
                    selected_index = index
                    break

        pool.rotate(-selected_index)
        selected = pool.popleft()
        pool.rotate(selected_index)

        result.append(selected)
        previous_artist = _primary_artist(selected)

    return result
