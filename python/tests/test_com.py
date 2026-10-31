import json

import pytest

from msauto import com


def test_parse_json_plain_object():
    assert com._parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_picks_last_json_line():
    text = "noise\n{\"a\": 1}\nmore\n{\"b\": 2}\n"
    assert com._parse_json(text) == {"b": 2}


def test_parse_json_returns_raw_for_non_json():
    assert com._parse_json("just text") == {"raw": "just text"}


def test_find_msctl_honours_env(tmp_path, monkeypatch):
    exe = tmp_path / "msctl.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setenv("MSAUTO_MSCTL", str(exe))
    assert com.find_msctl() == exe


def test_find_msctl_rejects_missing_env_target(tmp_path, monkeypatch):
    monkeypatch.setenv("MSAUTO_MSCTL", str(tmp_path / "nope.exe"))
    with pytest.raises(FileNotFoundError):
        com.find_msctl()


def test_find_msctl_falls_back_to_repo_layout(monkeypatch):
    monkeypatch.delenv("MSAUTO_MSCTL", raising=False)
    monkeypatch.setattr(com.shutil, "which", lambda name: None)
    # The repository build lives at <repo>/csharp/bin/msctl.exe next to python/.
    repo_exe = com.Path(com.__file__).resolve().parents[3] / "csharp" / "bin" / "msctl.exe"
    if not repo_exe.is_file():
        pytest.skip("msctl.exe has not been built in this checkout")
    assert com.find_msctl() == repo_exe


def test_run_raises_on_error_payload(monkeypatch):
    class Proc:
        returncode = 0
        stdout = json.dumps({"error": "boom", "detail": "because"})
        stderr = ""

    monkeypatch.setattr(com, "find_msctl", lambda: "msctl.exe")
    monkeypatch.setattr(com.subprocess, "run", lambda *a, **k: Proc())
    with pytest.raises(com.MsCtlError) as excinfo:
        com.run("introspect", "x.ms14")
    assert "because" in str(excinfo.value)
