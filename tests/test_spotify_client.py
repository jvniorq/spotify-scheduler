from types import SimpleNamespace

import pytest

from spotify_scheduler_pro.config import AppConfig
from spotify_scheduler_pro.spotify_client import SpotifyService


def test_failed_connection_does_not_publish_client(monkeypatch) -> None:
    class FailingClient:
        def current_user(self):
            raise RuntimeError("oauth failed")

    manager = SimpleNamespace(get_client_secret=lambda: "secret")
    paths = SimpleNamespace(oauth_cache=SimpleNamespace(unlink=lambda **_kwargs: None))
    storage = SimpleNamespace()

    monkeypatch.setattr(
        "spotify_scheduler_pro.spotify_client.SpotifyOAuth",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr(
        "spotify_scheduler_pro.spotify_client.spotipy.Spotify",
        lambda **_kwargs: FailingClient(),
    )

    service = SpotifyService(manager, paths, storage)
    with pytest.raises(RuntimeError, match="oauth failed"):
        service.connect(AppConfig(client_id="client"))

    assert not service.connected
