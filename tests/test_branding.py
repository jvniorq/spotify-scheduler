
from spotify_scheduler_pro import __version__
from spotify_scheduler_pro.branding import (
    ARTIFACT_NAME,
    DISPLAY_NAME,
    EXECUTABLE_NAME,
    LEGACY_AUTOSTART_NAME,
    LEGACY_DATA_DIR_NAME,
    LEGACY_KEYRING_SERVICE,
    LEGACY_OAUTH_SERVICE,
    PLAYLIST_EXPORT_FORMAT,
    TAGLINE,
    TECHNICAL_PACKAGE,
    VERSION,
    WINDOW_TITLE,
)


def test_public_spoxu_identity_is_consistent() -> None:
    assert DISPLAY_NAME == "Spoxu"
    assert VERSION == __version__ == "0.2.0"
    assert TAGLINE in WINDOW_TITLE
    assert WINDOW_TITLE.startswith(DISPLAY_NAME)
    assert EXECUTABLE_NAME == "Spoxu"
    assert ARTIFACT_NAME == "Spoxu-Windows"


def test_technical_compatibility_identifiers_are_stable() -> None:
    assert TECHNICAL_PACKAGE == "spotify_scheduler_pro"
    assert LEGACY_DATA_DIR_NAME == "SpotifySchedulerPro"
    assert LEGACY_KEYRING_SERVICE == "SpotifySchedulerPro"
    assert LEGACY_OAUTH_SERVICE == "SpotifySchedulerProOAuth"
    assert LEGACY_AUTOSTART_NAME == "SpotifySchedulerPro"
    assert PLAYLIST_EXPORT_FORMAT == "spotify-scheduler-pro-playlist-v1"
