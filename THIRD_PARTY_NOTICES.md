# Third-party notices

## multisim-mcp

The netlist-to-schematic builder used by the examples lives in the separate
`multisim-mcp` project by the Multisim MCP contributors and is distributed
under the MIT license:

> MIT License
>
> Copyright (c) 2026 Multisim MCP contributors
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

msauto does not vendor that project; it imports it as a dependency when you
build schematics.

## National Instruments / Multisim

This project is not affiliated with, endorsed by, or sponsored by National
Instruments. Multisim and NI are trademarks of National Instruments.

No National Instruments software, component library, template, symbol, sample
project or other licensed asset is included in this repository. The COM interop
assembly is generated locally on the user's machine from the type library that
ships with the user's own licensed Multisim installation. Template packs built
with `docs/template-packs.md` are for the user's local use only and must not be
redistributed.
