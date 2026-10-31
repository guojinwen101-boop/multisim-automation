# Contributing

Thanks for helping. A few rules keep this project safe to share:

## Do not commit NI content

Nothing extracted from a Multisim installation may enter the repository:

* no component templates (`.xml` template packs),
* no `.ms14` / `.ms7` circuits (they embed templates),
* no screenshots containing template XML or NI sample circuits.

`.gitignore` blocks the common paths; double-check `git status` before a commit
that touches XML or circuit files.

## Code

* Python: 3.9+, standard library only. Run the tests before sending a change:
  `python -m pytest python/tests -q`.
* C#: must stay compatible with the .NET Framework 4 compiler (C# 5 — no
  string interpolation, no pattern matching).
* Keep `msctl` stdout machine-readable: one JSON object per run, progress on
  stderr.

## Documentation

Behaviour that took hours to discover belongs in `docs/` — the COM notes file
is the most valuable part of this repository. If a workaround surprises you,
write it down.
