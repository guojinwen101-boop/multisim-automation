from msauto.netlist import elements, format_issues, lint

CLEAN = """* a small valid netlist
V1 in 0 DC 5
R1 in out 1k
C1 out 0 1u
AU1 clk q vdd 0 74LS161
.end
"""


def test_clean_netlist_has_no_issues():
    assert lint(CLEAN) == []


def test_bare_one_is_flagged_on_digital_lines():
    text = "AU1 1 0 0 vdd 74LS85\n.end\n"
    issues = lint(text)
    assert len(issues) == 1
    assert issues[0].level == "warning"
    assert "vdd" in issues[0].message
    assert issues[0].line == 1


def test_bare_one_is_fine_on_analog_elements():
    # A resistor between nodes "1" and "2" is legal — only A-lines get the warning.
    assert lint("R1 1 2 10\n.end\n") == []


def test_duplicate_names_are_errors():
    issues = lint("R1 a b 1k\nR1 b c 1k\n.end\n")
    assert any(i.level == "error" and "duplicate" in i.message for i in issues)
    assert issues[0].line == 2


def test_missing_end_is_an_error():
    issues = lint("R1 a b 1k\n")
    assert any("no .end" in i.message for i in issues)


def test_short_line_is_a_warning():
    issues = lint("R1 a\n.end\n")
    assert any(i.level == "warning" and "token" in i.message for i in issues)


def test_elements_skips_comments_and_dot_lines():
    assert [name for name, _ in elements(CLEAN)] == ["V1", "R1", "C1", "AU1"]


def test_format_issues_mentions_line_numbers():
    text = format_issues(lint("R1 a\n"))
    assert "warning:1" in text
