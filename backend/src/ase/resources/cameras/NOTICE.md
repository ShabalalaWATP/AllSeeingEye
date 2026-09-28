# Curated European camera catalogues

The twelve country files in this folder (`bulgaria.json`, `czechia.json`, `france.json`,
`germany.json`, `italy.json`, `macedonia.json`, `poland.json`, `romania.json`,
`serbia.json`, `slovakia.json`, `spain.json` and `switzerland.json`) are public camera
catalogues generated from the OSIRIS CCTV modules by simplifaisoul at commit `fac8d1b`:
<https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv>.

Records keep the upstream identifiers, names, approximate coordinates, provider links and
source names unchanged. `ase.adapters.geo.camera_europe_catalogue` reads only these fixed
files, rejects any record whose shape it does not expect, and the camera adapter still
checks coordinates and media origins before a camera is shown. Positions are reference
locations, not surveyed camera installations, and a listed stream is not an assertion that
it is currently broadcasting. See `docs/CAMERA_EUROPE.md` for observed availability.

The licence below applies to the copied catalogue portion only, not to third-party camera
imagery or streams. Each provider's own terms still apply.

```text
MIT License

Copyright (c) 2026 simplifaisoul

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
