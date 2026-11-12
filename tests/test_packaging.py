"""What the package has to ship for its typing work to reach a consumer."""

from __future__ import annotations

from importlib.resources import files


def test_the_package_ships_a_py_typed_marker():
    """Without the marker, a consumer's mypy sees ``matcha.*`` as ``Any`` (verified)."""
    assert files("matcha").joinpath("py.typed").is_file()
