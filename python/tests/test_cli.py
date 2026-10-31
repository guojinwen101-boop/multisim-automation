from msauto import cli


def test_lint_clean_file(tmp_path, capsys):
    net = tmp_path / "ok.net"
    net.write_text("R1 a b 1k\n.end\n", encoding="utf-8")
    assert cli.main(["lint", str(net)]) == 0
    assert "no issues found" in capsys.readouterr().out


def test_lint_error_exits_nonzero(tmp_path, capsys):
    net = tmp_path / "bad.net"
    net.write_text("R1 a b 1k\n", encoding="utf-8")   # no .end
    assert cli.main(["lint", str(net)]) == 1
    assert "no .end" in capsys.readouterr().out


def test_lint_strict_fails_on_warnings(tmp_path):
    net = tmp_path / "warn.net"
    net.write_text("AU1 1 0 0 vdd 74LS85\n.end\n", encoding="utf-8")
    assert cli.main(["lint", str(net)]) == 0
    assert cli.main(["lint", str(net), "--strict"]) == 1


def test_pack_validate_missing_dir(tmp_path, capsys):
    assert cli.main(["pack", "validate", str(tmp_path / "missing")]) == 1
    assert "not a directory" in capsys.readouterr().out
