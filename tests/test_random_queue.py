import random

from spotify_scheduler_pro.random_queue import build_random_queue


def test_random_queue_filters_duplicates_local_and_recent() -> None:
    tracks = [
        {"uri": "spotify:track:1", "artists": [{"id": "a"}]},
        {"uri": "spotify:track:1", "artists": [{"id": "a"}]},
        {"uri": "spotify:local:bad", "artists": [{"id": "b"}]},
        {"uri": "spotify:track:2", "artists": [{"id": "b"}]},
        {"uri": "spotify:track:3", "artists": [{"id": "c"}]},
    ]
    result = build_random_queue(
        tracks,
        recent_uris={"spotify:track:3"},
        max_tracks=10,
        rng=random.Random(1),
    )
    uris = [track["uri"] for track in result]
    assert len(uris) == 2
    assert "spotify:local:bad" not in uris
    assert "spotify:track:3" not in uris
    assert len(set(uris)) == len(uris)


def test_random_queue_avoids_consecutive_artists_when_possible() -> None:
    tracks = [
        {"uri": "spotify:track:1", "artists": [{"id": "a"}]},
        {"uri": "spotify:track:2", "artists": [{"id": "a"}]},
        {"uri": "spotify:track:3", "artists": [{"id": "b"}]},
    ]
    result = build_random_queue(tracks, rng=random.Random(3))
    artists = [track["artists"][0]["id"] for track in result]
    assert not (artists[0] == artists[1] == "a")
