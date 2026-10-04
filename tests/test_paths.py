import os
import sys
from pathlib import Path

import pytest

from app.core.paths import (
    UnsafePathError,
    is_within,
    resolve_in_any,
    resolve_safe,
    safe_filename
)


@pytest.fixture
def tree(tmp_path):

    base = tmp_path / "base"
    (base / "sub").mkdir(parents=True)
    (base / "sub" / "inside.txt").write_text("ok")
    (base / "top.txt").write_text("ok")

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("no")

    return base, outside


def test_resolves_relative_and_absolute_paths_inside_base(tree):

    base, _ = tree

    assert resolve_safe(base, "top.txt") == (base / "top.txt").resolve()
    assert resolve_safe(base, "sub/inside.txt") == (base / "sub" / "inside.txt").resolve()
    assert resolve_safe(base, str(base / "sub" / "inside.txt")) == (base / "sub" / "inside.txt").resolve()
    # ".." that stays inside the base is fine.
    assert resolve_safe(base, "sub/../top.txt") == (base / "top.txt").resolve()


@pytest.mark.parametrize("attack", [
    "../outside/secret.txt",
    "..\\outside\\secret.txt",
    "sub/../../outside/secret.txt",
    "..%2foutside%2fsecret.txt",
    "..%5coutside%5csecret.txt",
    "%2e%2e%2foutside%2fsecret.txt",
    "..%252foutside%252fsecret.txt",
])
def test_traversal_is_rejected(tree, attack):

    base, _ = tree

    with pytest.raises(UnsafePathError):
        resolve_safe(base, attack)


def test_absolute_path_outside_base_is_rejected(tree):

    base, outside = tree

    with pytest.raises(UnsafePathError):
        resolve_safe(base, str(outside / "secret.txt"))


@pytest.mark.skipif(sys.platform != "win32", reason="Windows drive letters")
def test_drive_letter_paths_are_rejected(tree):

    base, _ = tree

    for attack in ("C:\\", "C:\\Windows\\win.ini", "C:/Windows/win.ini", "C:Windows\\win.ini"):
        with pytest.raises(UnsafePathError):
            resolve_safe(base, attack)


@pytest.mark.parametrize("attack", [
    "\\\\server\\share\\file.txt",
    "//server/share/file.txt",
    "\\\\?\\C:\\Windows\\win.ini",
    "\\\\127.0.0.1\\c$\\Windows\\win.ini",
])
def test_unc_paths_are_rejected(tree, attack):

    base, _ = tree

    with pytest.raises(UnsafePathError):
        resolve_safe(base, attack)


def test_symlink_escaping_base_is_rejected(tree):

    base, outside = tree
    link = base / "escape"

    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks needs Developer Mode / admin on Windows")

    with pytest.raises(UnsafePathError):
        resolve_safe(base, "escape/secret.txt")


def test_symlink_inside_base_is_allowed(tree):

    base, _ = tree
    link = base / "alias.txt"

    try:
        os.symlink(base / "top.txt", link)
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks needs Developer Mode / admin on Windows")

    assert resolve_safe(base, "alias.txt") == (base / "top.txt").resolve()


@pytest.mark.parametrize("bad", ["", "   ", "missing.txt", "top.txt\x00.pdf"])
def test_empty_missing_and_null_byte_inputs(tree, bad):

    base, _ = tree

    with pytest.raises(UnsafePathError):
        resolve_safe(base, bad)


def test_missing_base_is_rejected(tmp_path):

    with pytest.raises(UnsafePathError):
        resolve_safe(tmp_path / "nope", "x.txt")


def test_sibling_prefix_is_not_inside(tmp_path):

    base = tmp_path / "data"
    sibling = tmp_path / "data-evil"
    base.mkdir()
    sibling.mkdir()
    (sibling / "x.txt").write_text("no")

    assert not is_within(sibling.resolve(), base.resolve())

    with pytest.raises(UnsafePathError):
        resolve_safe(base, "../data-evil/x.txt")


def test_is_within_is_case_insensitive_on_windows(tmp_path):

    if sys.platform != "win32":
        pytest.skip("Windows only")

    assert is_within(Path(str(tmp_path).upper()) / "a", tmp_path)


def test_resolve_in_any(tree):

    base, outside = tree

    assert resolve_in_any([outside, base], "top.txt") == (base / "top.txt").resolve()
    assert resolve_in_any([base], "../outside/secret.txt") is None


@pytest.mark.parametrize("name", [
    "../x.pdf", "..\\x.pdf", "a/b.pdf", "a\\b.pdf", "..", ".", "",
    "C:x.pdf", "con:stream", "%2e%2e%2fx.pdf", "x\x00.pdf", "x?.pdf", "a" * 256,
])
def test_safe_filename_rejects(name):

    with pytest.raises(UnsafePathError):
        safe_filename(name)


def test_safe_filename_accepts_plain_names():

    assert safe_filename("report final (2).pdf") == "report final (2).pdf"
    assert safe_filename("notes.v2.txt") == "notes.v2.txt"


@pytest.mark.skipif(sys.platform != "win32", reason="NTFS junctions")
def test_junction_escaping_base_is_rejected(tree):
    """Junctions need no admin rights, so this always exercises link-following."""

    import subprocess

    base, outside = tree
    link = base / "junction"

    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    assert (link / "secret.txt").exists()

    with pytest.raises(UnsafePathError):
        resolve_safe(base, "junction/secret.txt")
