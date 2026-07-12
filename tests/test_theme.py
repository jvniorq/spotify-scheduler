
from spotify_scheduler_pro.theme import METRICS, PALETTE, contrast_ratio, is_hex_color


def test_theme_tokens_are_valid_hex_colors() -> None:
    required = {
        "background",
        "header",
        "surface",
        "elevated",
        "border",
        "text",
        "muted",
        "accent",
        "secondary",
        "success",
        "warning",
        "danger",
        "selection",
        "console",
    }
    assert required <= PALETTE.keys()
    assert all(is_hex_color(color) for color in PALETTE.values())


def test_theme_text_has_accessible_contrast() -> None:
    assert contrast_ratio(PALETTE["text"], PALETTE["background"]) >= 7
    assert contrast_ratio(PALETTE["text"], PALETTE["surface"]) >= 7
    assert contrast_ratio(PALETTE["muted"], PALETTE["background"]) >= 4.5


def test_theme_metrics_are_positive() -> None:
    assert all(value > 0 for value in METRICS.values())
