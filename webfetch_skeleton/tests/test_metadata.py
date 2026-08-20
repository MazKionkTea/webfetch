"""
test_metadata.py
Test ekstraksi & prioritas sumber metadata: JSON-LD > OG > meta > title.
"""


def test_json_ld_takes_priority_over_og_tags():
    """TODO: kalau JSON-LD & OG tag beda, JSON-LD yang dipakai."""
    pass


def test_falls_back_to_title_tag_when_no_other_source():
    """TODO: kalau tidak ada meta/OG/JSON-LD sama sekali, pakai <title>."""
    pass
