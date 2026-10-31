import pytest

from msauto.simulate import Simulation
from msauto.verify import CheckFailure, Checks


@pytest.fixture()
def sim():
    return Simulation(
        time=[0.0, 0.001, 0.002],
        signals={"a": [0.0, 5.0, 5.0], "b": [0.0, 0.0, 4.0]},
    )


def test_interpolation_and_digital(sim):
    assert sim.at("a", 0.0005) == pytest.approx(2.5)
    assert sim.digital("a", 0.0005) == 0   # exactly at threshold -> not high
    assert sim.digital("a", 0.0006) == 1
    assert sim.digital("b", 0.002) == 1


def test_accessors_are_helpful(sim):
    with pytest.raises(KeyError) as excinfo:
        sim.signal("nope")
    assert "available" in str(excinfo.value)
    assert sim.names == ["a", "b"]
    assert len(sim) == 3


def test_edges(sim):
    assert sim.edges("a") == [(0.001, 1)]
    assert sim.edges("b") == [(0.002, 1)]


def test_all_checks_pass(sim, capsys):
    chk = Checks(sim)
    chk.expect_digital("a", 0.0015, 1, "a is high late")
    chk.expect_low("b", 0.0015, "b is still low")
    chk.expect_between("b", 0.002, 3.9, 4.1, "b settles near 4 V")
    assert chk.report() is True
    out = capsys.readouterr().out
    assert "3 passed, 0 failed" in out


def test_failure_is_reported(sim, capsys):
    chk = Checks(sim)
    chk.expect_high("b", 0.0015, "b should be high")
    assert chk.ok is False
    assert chk.report() is False
    assert "[FAIL] b should be high" in capsys.readouterr().out

    with pytest.raises(CheckFailure) as excinfo:
        chk.raise_for_failures()
    assert "b should be high" in str(excinfo.value)


def test_custom_threshold(sim):
    chk = Checks(sim, threshold=4.5)
    assert chk.digital("b", 0.002) == 0
