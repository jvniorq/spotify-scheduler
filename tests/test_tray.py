
from spotify_scheduler_pro.tray import _make_icon


def test_spoxu_tray_icon_has_brand_identity() -> None:
    icon = _make_icon()
    assert icon.mode == "RGBA"
    assert icon.size == (64, 64)
    colors = {color for _count, color in icon.getcolors(maxcolors=4096) or []}
    assert (124, 92, 252, 255) in colors
    assert (56, 214, 199, 255) in colors
    assert len(colors) >= 5
