import pytest

from msauto.template_pack import build_pack, list_parts, validate_pack


def make_part(directory, kind, ports=2, symbol=True):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{kind}_element.xml").write_text("<element/>", encoding="utf-8")
    if symbol:
        (directory / f"sym_{kind}.xml").write_text("<symbol/>", encoding="utf-8")
    for index in range(1, ports + 1):
        (directory / f"{kind}_port{index}.xml").write_text("<port/>", encoding="utf-8")


def test_list_parts_basic(tmp_path):
    make_part(tmp_path, "d85")
    parts = list_parts(tmp_path)
    assert list(parts) == ["d85"]
    assert parts["d85"].complete
    assert len(parts["d85"].ports) == 2


def test_validate_reports_missing_symbol_and_ports(tmp_path):
    make_part(tmp_path, "d85", ports=0, symbol=False)
    problems = validate_pack(tmp_path)
    assert any("missing symbol" in p for p in problems)
    assert any("no port files" in p for p in problems)


def test_validate_reports_orphan_symbol(tmp_path):
    make_part(tmp_path, "d85")
    (tmp_path / "sym_orphan.xml").write_text("<symbol/>", encoding="utf-8")
    assert any("orphan" in p for p in validate_pack(tmp_path))


def test_build_pack_overlays_part_dirs(tmp_path):
    base = tmp_path / "base"
    make_part(base, "d84")
    extra = tmp_path / "extra"
    make_part(extra, "d85")
    out = tmp_path / "out"

    result = build_pack(base, [extra], out)
    assert result["problems"] == []
    assert set(result["parts"]) == {"d84", "d85"}
    assert "d85_element.xml" in result["overlaid"]


def test_build_pack_refuses_existing_output(tmp_path):
    base = tmp_path / "base"
    make_part(base, "d84")
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(FileExistsError):
        build_pack(base, [], out)
    # ... unless overwrite is explicit.
    result = build_pack(base, [], out, overwrite=True)
    assert result["parts"] == ["d84"]
