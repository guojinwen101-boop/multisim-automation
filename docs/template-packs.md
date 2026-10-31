# Template packs (local only)

Multisim does not let you create a component from a SPICE line alone: every
schematic object carries a *template* (element definition, symbol drawing, one
port file per pin). The builder needs those XML fragments.

They are **licensed NI content**. This repository therefore ships code only, and
each user derives a pack from their own installation.

## What a pack looks like

```
my-pack/
├─ d85_element.xml        component template: attributes + SPICE card
├─ sym_d85.xml            symbol graphics
├─ d85_port1.xml …        one file per pin
├─ d48_element.xml
├─ sym_d48.xml
├─ d48_port1.xml …
└─ …
```

`msauto pack list <dir>` shows what a pack contains; `msauto pack validate <dir>`
reports missing symbols or port files.

## Extracting a pack

Use the upstream tool that ships with the multisim-mcp project:

```bat
python tools\bootstrap_local_component_pack.py --output C:\my-pack
```

It reads a handful of NI's own sample circuits that are installed with
Multisim (RLC values, LowPassFilter, ClassBPushPullAmp, …), pulls the
templates for R, C, V, GND, D, QNPN and friends out of them, and writes a pack.
No master-database file is copied.

Set the builder environment before building:

```bat
set MULTISIM_MCP_TEMPLATE_DIR=C:\my-pack
set MULTISIM_MCP_TEMPLATE_ONLY=1
```

`MULTISIM_MCP_TEMPLATE_ONLY=1` stops the builder from silently falling back to
other sources, so a missing part fails loudly instead of producing an empty
component.

## Adding parts the bootstrap does not cover

Two routes:

1. **Extract from your own design.** Open a circuit that already contains the
   part in Multisim, save it as `.ms14`, and pull the object out with the
   upstream `extract_native_component_templates.py` tool. Add the resulting
   files to your pack.
2. **Synthesize a digital part.** A digital IC template is: a SPICE template
   line pointing at a model card, plus a symbol and ports. You can clone the
   carrier (e.g. a 74LS191 template), remap pin names/numbers, and swap in the
   model card for the part you want. This is how the 74LS161/74LS160 models in
   the overload example were produced. Two details matter:
   * keep the real newlines inside XML attributes — Multisim's template is a
     list of `+` continuation lines and the model card is a quoted block whose
     `;` comments must end at a newline; an XML parser that normalises
     attribute whitespace silently destroys the model;
   * give every synthesized part its own model reference id, otherwise the
     builder's cache hands the second part the first part's model card.

Assemble the result with:

```bat
msauto pack build --base C:\my-pack --part C:\extracted\ls161 --out C:\my-pack-complete
```

## Policy

* Never commit a pack, or anything extracted from it, to this repository.
  `.gitignore` already excludes the usual directory names.
* Do not publish packs, mirrors of them, or screenshots that embed them.
* The pack works only on a machine with a licensed Multisim installation.
