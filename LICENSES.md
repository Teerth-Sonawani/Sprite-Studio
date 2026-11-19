# Licensing Status

This file records the licensing position of the workspace. It is not legal
advice. The repository owner must review it before distribution.

## Original workspace code and demo art

Unless the repository owner replaces this notice, the original Python code,
documentation, configuration, templates and procedural demo art created for this
workspace are offered under the MIT License:

```text
MIT License

Copyright (c) 2026 2D Sprite Studio contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The example project's art is original procedural demo art. It does not copy a
franchise character, logo or named artist's work. It is included to demonstrate
the pipeline, not as a claim of production art quality.

## Generated assets

Assets generated through a provider are subject to that provider's terms, the
model's licence and the project's own agreements. The workspace records
provider, mode and model key in every manifest, but provenance metadata is not a
licence grant. Verify the provider terms before distribution.

## Third-party dependencies

| Dependency | Typical licence | Notes |
|---|---|---|
| Pillow | HPND | Image I/O and drawing |
| NumPy | BSD-3-Clause | Array processing |
| PyYAML | MIT | Configuration parsing |
| jsonschema | MIT | Manifest validation |
| imageio | BSD-2-Clause | Optional video preview I/O |
| imageio-ffmpeg | BSD-2-Clause plus bundled FFmpeg terms | Optional MP4/WebM previews |
| SciPy | BSD-3-Clause | Optional faster labelling |
| OpenCV | Apache-2.0 | Optional; not required by the current pipeline |
| pytest | MIT | Test runner |
| FFmpeg (system or bundled) | LGPL-2.1+ or GPL depending on build | Video encoding; check the exact build |

This table is a summary, not a replacement for each project's licence text.

## Fonts and external references

The workspace does not bundle third-party fonts. `Pillow`'s default font is used
for labels when DejaVuSans is unavailable. Style references describe visual
characteristics; they do not grant rights to imitate a named artist or a
protected character.

## Before release

- [ ] Replace or confirm the MIT notice with the project owner's chosen licence.
- [ ] Confirm provider terms and model licences for every generated asset.
- [ ] Confirm that no prompt requested a protected character, logo or artist
      imitation.
- [ ] Keep the provenance sidecar and manifest with every distributed asset.
- [ ] Review the FFmpeg build's licence if MP4/WebM previews are redistributed.
