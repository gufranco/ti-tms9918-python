# TI TMS9918

The Texas Instruments TMS9918A, TMS9928A and TMS9929A video display processors in Python, advanced one master clock tick at a time and held to TI's 1982 data manual.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/ti-tms9918-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/ti-tms9918-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/ti-tms9918-python)](https://github.com/gufranco/ti-tms9918-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**348** distinct SG-1000 images booted for **600** frames each, **0** property failures over the **203** retail ones, **64** quotes located in the manual, **3** parts, **820** tests, **100%** statement and branch coverage, no dependencies

```python
import tms9918

part = tms9918.Chip("tms9918a")
part.reset()
part.read_status()

for register, value in {1: 0x40, 2: 0x06, 3: 0x80, 4: 0x00, 7: 0x04}.items():
    part.write_control(value)
    part.write_control(0x80 | register)

for address, value in {0x1800: 0x01, 0x0008: 0x80, 0x2000: 0xF0}.items():
    part.write_control(address & 0xFF)
    part.write_control(0x40 | address >> 8)
    part.write_data(value)
    part.run_dots(16)

while (part.line, part.dot) != (0, 0):
    part.clock()

shown = []
for _ in range(3):
    part.clock()
    shown.append((part.region, part.colour))
print(shown)
print(part.model, part.line, part.dot)
```

```
[('active', 15), ('active', 4), ('active', 4)]
tms9918a 0 3
```

A part powers up with scrambled registers and video memory, so the example resets it and reads the status once to clear the address latch. Five register writes turn the display on in Graphics I with a dark blue backdrop. Three data writes go through the ports, and each lands in video memory at the processor's next access window. The first cell of the first line is pattern 1, whose top row starts with one white dot.

## Install

| Requirement | Version                     |
| :---------- | :-------------------------- |
| Python      | 3.12 or newer               |
| git         | Any, to fetch the submodule |

```bash
git clone --recurse-submodules https://github.com/gufranco/ti-tms9918-python.git
cd ti-tms9918-python
python3 tms9918/doctor.py
```

The package imports nothing outside the standard library. The submodule is `zilog-z80-python`, and only the census uses it. A source archive from the download-zip link has no submodule: there the census and its tests report why they cannot run, and everything else works.

The doctor checks the machine and the checkout and ends with one line. Paste its whole output into any bug report.

```
  10 checks, nothing to report
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/ti-tms9918-python/releases).

## The interface

`tms9918.Chip(model, memory=None, seed=UNSET_SEED)` builds one part. `model` is required. `memory` is any object with `read8(address)` and `write8(address, value)`, and the part builds a scrambled 16 KB `Vram` when it is left out. `seed` sets the power-on scramble of the registers and of that `Vram`.

| Model      | Aliases | Lines | Frame rate  | Video output                                | CPUCLK and GROMCLK pins |
| :--------- | :------ | :---- | :---------- | :------------------------------------------ | :---------------------- |
| `tms9918a` | `9918a` | 262   | About 60 Hz | Composite                                   | Yes                     |
| `tms9928a` | `9928a` | 262   | About 60 Hz | Luminance and two colour difference signals | No                      |
| `tms9929a` | `9929a` | 313   | About 50 Hz | Luminance and two colour difference signals | No                      |

### Calls

| Call                   | Effect                                                                                                                                 |
| :--------------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| `reset()`              | What the RESET pin does: clears registers 0 and 1 and the three status flags, and moves the beam to the top blanking. Returns the part |
| `write_control(value)` | One byte to the control port: half of a video memory address, or half of a register write                                              |
| `write_data(value)`    | One byte to video memory. It lands at the next access window                                                                           |
| `read_data()`          | Returns the read buffer, then fetches the next byte at the next access window                                                          |
| `read_status()`        | Returns the status byte and clears the F, 5S and C flags                                                                               |
| `tick()`               | One master clock period. Returns the `CPUCLK` and `GROMCLK` edges on the TMS9918A, and 0 on the other parts                            |
| `clock()`              | One dot, which is two ticks                                                                                                            |
| `run_dots(count)`      | `count` dots                                                                                                                           |

### State

| Attribute   | Meaning                                                                                                                                                             |
| :---------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `line`      | Line number, counted from the first active line                                                                                                                     |
| `dot`       | Dot number, counted from the first dot of a pattern-mode active area                                                                                                |
| `region`    | `active`, `border`, `blanking`, `sync` or `burst` for the last dot                                                                                                  |
| `colour`    | Colour index 0 to 15 of the last dot, `EXTERNAL` where external video shows through, or `None` where nothing is drawn. A transparent backdrop shows black, colour 1 |
| `interrupt` | True while the INT pin is asserted                                                                                                                                  |
| `status`    | The status byte, read without clearing anything                                                                                                                     |
| `registers` | The eight write-only registers as a `bytearray`                                                                                                                     |
| `mode`      | The display mode the registers select, such as `graphics1`, `graphics2`, `multicolor`, `text` or a combination such as `text+graphics2`                             |
| `model`     | The canonical model name                                                                                                                                            |
| `part`      | The `Model` record: `lines`, `output`, `clock_pins`, `aliases`, `summary`                                                                                           |
| `memory`    | The video memory object                                                                                                                                             |
| `cycles`    | Master clock ticks since the part was built                                                                                                                         |

### Module contents

| Name                                                      | Content                                                                                                                                                                                                |
| :-------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tms9918.MODELS`                                          | The three `Model` records, keyed by canonical name                                                                                                                                                     |
| `tms9918.Vram(fill=None, seed=UNSET_SEED)`                | 16 KB of video memory. `fill` is a byte value or a byte string, and without it the contents are scrambled from `seed`                                                                                  |
| `tms9918.UnknownModelError`                               | Raised for a missing or unknown model name. The message lists the names accepted                                                                                                                       |
| `tms9918.CPUCLK`, `tms9918.GROMCLK`                       | The bits in `tick()`'s return value that mark a pulse on each clock pin. CPUCLK pulses every 3 ticks and GROMCLK every 24                                                                              |
| `tms9918.EXTERNAL`                                        | The `colour` value where external video shows through                                                                                                                                                  |
| `tms9918.COMPOSITE`, `tms9918.DIFFERENCE`                 | The signal levels Table 2-3 prints for each colour                                                                                                                                                     |
| `tms9918.COMPOSITE_SPECIAL`, `tms9918.DIFFERENCE_SPECIAL` | The levels Table 2-3 prints for black, sync, the colour burst and external video. `COMPOSITE_SPECIAL` holds `black`, `burst` and `sync`, and `DIFFERENCE_SPECIAL` holds `black`, `sync` and `external` |
| `tms9918.burst(model)`                                    | The colour burst on the two colour difference outputs of the `tms9928a` or the `tms9929a`                                                                                                              |
| `tms9918.__version__`                                     | The installed version                                                                                                                                                                                  |

```python
import tms9918

for name, model in tms9918.MODELS.items():
    print(name, model.aliases, model.lines, model.output, model.clock_pins)

print(tms9918.COMPOSITE[0xF], tms9918.DIFFERENCE[0x4], tms9918.burst("tms9929a"))

try:
    tms9918.Chip("tms9938")
except tms9918.UnknownModelError as error:
    print(error)
```

```
tms9918a ('9918a',) 262 composite True
tms9928a ('9928a',) 262 colour difference False
tms9929a ('9929a',) 313 colour difference False
(1.0, None) (0.4, 0.4, 1.0) (0.0, 0.73, 0.2)
tms9938 is not a model this package covers; it has tms9918a, tms9928a, tms9929a
```

`COMPOSITE` maps each colour index to its luminance and chrominance levels, with `None` where the table prints no chrominance. `DIFFERENCE` maps each colour index to its luminance and the two colour difference levels. Both are copied from Table 2-3 as printed.

### Frame length per model

```python
import tms9918


def frame(part):
    part.read_status()
    dots = 0
    while not part.status & 0x80:
        part.clock()
        dots += 1
    return dots


for name in ("tms9918a", "tms9928a", "tms9929a"):
    part = tms9918.Chip(name)
    part.reset()
    frame(part)
    print(part.model, frame(part), frame(part) // 342, part.part.clock_pins)

print(tms9918.Chip("9929a").model)
```

```
tms9918a 89604 262 True
tms9928a 89604 262 False
tms9929a 107046 313 False
tms9929a
```

A frame is 342 dots per line on every part. The first full frame after a reset is counted from one F flag to the next.

## Sprites and the status byte

```python
import tms9918
from tms9918.memory import Vram

part = tms9918.Chip("tms9928a", Vram(fill=0))
part.reset()
part.read_status()
for register, value in {1: 0x40, 5: 0x36, 6: 0x07}.items():
    part.write_control(value)
    part.write_control(0x80 | register)

for plane in range(5):
    entry = 0x1B00 + plane * 4
    part.memory.write8(entry, 49)
    part.memory.write8(entry + 1, plane * 6)
    part.memory.write8(entry + 3, 0x0F)
part.memory.write8(0x1B00 + 5 * 4, 0xD0)
part.memory.write8(0x3800, 0xFF)

while (part.line, part.dot) != (51, 0):
    part.clock()

status = part.read_status()
print(f"5S {bool(status & 0x40)}, fifth plane {status & 0x1F}, coincidence {bool(status & 0x20)}")
```

```
5S True, fifth plane 4, coincidence True
```

Five sprites share line 50. The part draws four, sets the 5S flag with the fifth sprite's plane number, 4, in the low bits, and sets the coincidence flag because the four drawn sprites overlap.

## The processor's access windows

The processor reaches video memory only in windows: once every 16 memory cycles in Graphics I and II with sprites, once every 3 in Text mode, and once every 4 in Multicolor, with no access waiting longer than about 8 microseconds. The manual does not say which dot each window falls on. This package takes the positions from openMSX's MSX1 tables and tests every bound TI printed against them.

openMSX records a measurement on a real MSX1: data writes 26 processor cycles apart or fewer corrupt video memory, and 27 or more never do. The model reproduces both halves. A second access that arrives while the first is still waiting replaces it, so the examples above let each write land before the next one.

```python
import tms9918
from tms9918.memory import Vram


def burst(gap):
    part = tms9918.Chip("tms9929a", Vram(fill=0))
    part.reset()
    part.read_status()
    part.write_control(0x40)
    part.write_control(0x81)
    while (part.line, part.dot) != (10, 0):
        part.clock()
    part.write_control(0x00)
    part.write_control(0x40)
    for value in (0x11, 0x22, 0x33):
        part.write_data(value)
        part.run_dots(gap)
    part.run_dots(400)
    return [hex(part.memory.read8(address)) for address in range(3)]


print(burst(12))
print(burst(41))
```

```
['0x0', '0x22', '0x33']
['0x11', '0x22', '0x33']
```

Three bytes go to a TMS9929A during the active display of a Graphics I frame. At 12 dots apart, the second byte arrives before the first has found a window, so the first byte is lost and the address has already moved on. At 41 dots apart, more than 27 cycles of a processor clocked at a third of the master clock, every byte lands.

## The census

```bash
python3 -m conformance.census "external/SG-1000" --frames 600 --jobs 10
```

The census boots every image in an SG-1000 library on an SG-1000 board, with the `zilog-z80-python` processor, and runs each for a fixed number of frames. It accepts directories, zip archives and single images, and counts each distinct image once by digest. It prints a summary, writes [`conformance/corpus.json`](conformance/corpus.json), and exits 1 when a property breaks.

Some cartridges carry their own RAM, among them Othello, The Castle and the Taiwanese Dahjee boards. [`conformance/boards.json`](conformance/boards.json) names each of those images by whole-file SHA-1 with its board, as MAME's SG-1000 software list records them, and the harness maps the RAM where that board puts it. Every other image runs on a plain board.

Two properties gate the run: the model raises no exception on any image, and every retail image turns its display on. Accesses requested before the previous one was served are counted and named per image but gate nothing, because shipped games do write faster than the windows allow and the chip loses those writes too. Hacks, homebrew, translations, betas, SC-3000 programs, `.sf` and `.sms` images and BIOS images never gate.

| Result of the last run                                                         | Count            |
| :----------------------------------------------------------------------------- | :--------------- |
| Distinct images                                                                | 348              |
| Graphics II                                                                    | 279              |
| Graphics I                                                                     | 47               |
| Text with the Graphics II bit set                                              | 4                |
| Multicolor                                                                     | 2                |
| Text                                                                           | 1                |
| Never turned the display on, none of them retail                               | 25               |
| Sprites 16 by 16, unmagnified                                                  | 261              |
| Sprites 8 by 8                                                                 | 66               |
| Sprites 16 by 16, magnified                                                    | 4                |
| Lost accesses on retail images, all in Champion Golf, Golgo 13 and Sega-Galaga | 47 over 7 images |
| Lost accesses on the rest, almost all from two homebrew titles                 | 12,629           |

[`conformance/corpus.json`](conformance/corpus.json) holds those counts and nothing from any cartridge, so the suite checks them on a machine with no library.

## Is it right

Every fact TI printed that a test can reach is held to the code. [`conformance/hardware.json`](conformance/hardware.json) carries each fact with its sentence and page, and [`conformance/hardware.test.py`](conformance/hardware.test.py) and [`conformance/display.test.py`](conformance/display.test.py) drive the part against them. `python3 -m conformance.quotes` finds every quoted sentence in the manual.

Every value the manual does not print sits under `notStated` in the same file, marked unverified, with its source and the measurement that would settle it. [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists them. The places where the manual contradicts itself are in [`conformance/divergences.json`](conformance/divergences.json).

## Working on it

| Need                                                            | Where                                                                 |
| :-------------------------------------------------------------- | :-------------------------------------------------------------------- |
| Every gate and the order to run them                            | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| The same material for a coding agent                            | [AGENTS.md](AGENTS.md)                                                |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md)                                                |
| Bug reports                                                     | [GitHub Issues](https://github.com/gufranco/ti-tms9918-python/issues) |
| Security reports                                                | [SECURITY.md](SECURITY.md)                                            |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 tms9918/core.test.py
```

Each module has a test file beside it, named after it, and each runs on its own as above. Coverage is a hard gate at 100% statement and branch.

## References

- _TMS9918A/TMS9928A/TMS9929A Video Display Processors Data Manual_, Texas Instruments, November 1982. 105 pages, 6,785,534 bytes, SHA-256 `3991f0c691b83036bbb96d8e60e8d4ed4cfbb5eed9567ad61737570771113450`. It is not redistributable and is not in this repository. `python3 -m conformance.documents` downloads it from https://bitsavers.org/components/ti/TMS9900/TMS9918A_TMS9928A_TMS9929A_Video_Display_Processors_Data_Manual_Nov82.pdf and refuses any other file.
- _TMS 9929A European Line Format Video Display Processor, Preliminary Data_, Texas Instruments, 24 March 1980. 20 pages, 7,934,967 bytes, SHA-256 `5d80fd454a3c5e5d1fe700ec6bb76ee3f70048577ffdc7da6833394b6f41bc9e`. Its page 10 is an earlier printing of Table 2-3 and settles the colour burst's decimal points. It is not in this repository. `python3 -m conformance.documents` downloads it from https://archive.org/download/tms-9929-a/TMS9929A.pdf and refuses any other file.
- openMSX, `src/video/VDPAccessSlots.cc` and `src/video/VDP.hh` at commit `99c28389d775b945c57be27df1def0925e28abd8`, https://github.com/openMSX/openMSX, for the access window positions. Facts only; no code is taken.
- MAME, `src/devices/video/tms9928a.cpp` at commit `dc00cf3517eef30587b33efbf1e1c63ad3531b58`, https://github.com/mamedev/mame, for behaviour neither the manual nor openMSX covers, and `hash/sg1000.xml` at the same commit for the cartridge boards. Facts only; no code is taken.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
