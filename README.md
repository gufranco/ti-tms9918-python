# TI TMS9918

The Texas Instruments TMS9918A, TMS9928A and TMS9929A video display processors, advanced one master clock tick at a time and held to TI's 1982 data manual.

[![CI](https://github.com/gufranco/ti-tms9918-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/ti-tms9918-python/actions/workflows/ci.yml)

**348** distinct SG-1000 images booted for **600** frames each, **0** property failures over the **203** retail ones, **62** quotes located in the manual, **3** parts, **633** tests, **100%** statement and branch coverage, no dependencies

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

The part comes up scrambled, so it is reset and its status read once, which clears the latch the way every real program does. Five registers turn the display on in Graphics I with a dark blue backdrop. Three data writes then go through the ports, each landing in video memory when the processor's next window comes round. The first cell of the first line is pattern 1, whose top row starts with one white dot.

## Install

```bash
git clone --recurse-submodules https://github.com/gufranco/ti-tms9918-python.git
```

The package imports nothing outside the standard library and needs Python 3.12 or newer. The submodule is `zilog-z80-python`, and only the census uses it. A source archive from the download-zip link carries no submodule, so in that checkout the census and its tests cannot run and say so, while everything else works.

Check what this machine looks like before anything else, and paste it into any report:

```bash
python3 tms9918/doctor.py
```

## The interface

`tms9918.Chip(model, memory)` builds a part. The model is `tms9918a`, `tms9928a` or `tms9929a`, also accepted as `9918a`, `9928a` and `9929a`. `memory` is a `Vram`, 16K bytes scrambled at power on, and the part builds its own when it is left out.

| Call | What it does |
|:--|:--|
| `reset()` | What the RESET pin does: clears registers 0 and 1 and the three status flags, and starts the frame at the top blanking. Returns the part |
| `write_control(value)` | One byte to the control port: half of an address or a register write |
| `write_data(value)` | One byte to video memory, landing at the next window |
| `read_data()` | The read buffer, then a fetch of the next byte at the next window |
| `read_status()` | The status byte, clearing F, 5S and C |
| `tick()` | One master clock period. Returns `CPUCLK` and `GROMCLK` edges on the TMS9918A, and 0 on the others |
| `clock()` | One dot, which is two ticks |
| `run_dots(count)` | That many dots |

After each dot, `region` is `active`, `border`, `blanking`, `sync` or `burst`, and `colour` is the colour index 0 to 15 shown there, or `EXTERNAL` where the external video shows through, or `None` where nothing is drawn. A transparent backdrop shows black, which is colour 1. `interrupt` is true while INT is asserted. `line` counts from the first active line and `dot` from the first dot of a pattern-mode active area.

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

The colour levels each part puts on its pins are in `tms9918.levels`, exactly as Table 2-3 prints them.

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

Five sprites share line 50, so four are drawn and the fifth is reported, and the four drawn overlap.

## The processor's windows

The manual says the processor gets a window into video memory once every 16 memory cycles in Graphics I and II with sprites, once every 3 in Text mode, and once every 4 in Multicolor, and that no access waits longer than about 8 microseconds. It never says which dot a window falls on. This package takes the positions from openMSX's MSX1 tables, which openMSX describes as measured on MSX1 hardware, and tests every bound TI printed against them. openMSX also records a measurement on a real MSX: data writes 26 processor cycles apart or fewer corrupt video memory, and 27 or more never do. The lead before a window counts here is set so that this model reproduces both halves. A second access that arrives while the first is still waiting replaces it, so the examples above let each write land before asking for the next.

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

Three bytes go out to a TMS9929A during the active display of a Graphics I frame. Twelve dots apart, the second byte arrives before the first has found a window, so the first never lands, while the address has already moved on. Forty one dots apart is more than 27 cycles of a processor clocked at a third of the master clock, and every byte lands.

## The census

`python3 -m conformance.census <library>` boots every image in an SG-1000 library on an SG-1000 board, behind the `zilog-z80-python` processor, and runs it for a fixed number of frames. Some cartridges carry their own RAM: Othello, The Castle and the Taiwanese Dahjee boards among them. [`conformance/boards.json`](conformance/boards.json) names each of those images by whole-file SHA-1 and its board, as MAME's SG-1000 software list records them, and the harness maps that RAM where the board puts it. Any other image runs on a plain board. The census counts the modes, register values and sprite settings that real software reaches. [`conformance/corpus.json`](conformance/corpus.json) holds those counts and nothing from any cartridge, so the suite replays them on a machine with no library.

Two properties gate the run: the model raises on no image, and every retail image turns its display on. Accesses asked for before the last one was served are counted and named, but they gate nothing. Shipped games do write faster than the windows allow, and on the chip those writes are lost too, by the measurement above. Hacks, homebrew, translations, betas, programs for the SC-3000 and the Master System, and BIOS images never gate.

Over the last run, 348 distinct images reached Graphics II on 279, Graphics I on 47, Text with the Graphics II bit set on 4, Multicolor on 2 and Text on 1. 25 never turned the display on, and none of those is retail. Sprites were 16 by 16 unmagnified on 261 images, 8 by 8 on 66 and 16 by 16 magnified on 4. Lost accesses came to 47 across 7 retail images, all Champion Golf, Golgo 13 and Sega-Galaga, and to 12,629 across the rest, almost all from two homebrew titles built for a slower clock.

## Is it right

Every fact TI printed that a test can reach is held to the code. [`conformance/hardware.json`](conformance/hardware.json) carries each with its sentence and page, [`conformance/hardware.test.py`](conformance/hardware.test.py) compares them with the constants here, and `python3 -m conformance.quotes` finds every sentence in the manual. Every value the manual does not print sits under `notStated` in the same file, marked unverified, with where it came from and the measurement that would settle it. [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists them. The places the manual contradicts itself are in [`conformance/divergences.json`](conformance/divergences.json).

## Working on it

[CONTRIBUTING.md](CONTRIBUTING.md) has every gate and the order to run them. [AGENTS.md](AGENTS.md) is the same material for an agent, and [FAMILY.md](FAMILY.md) is the standard this repository shares with the rest of the family.

## References

- *TMS9918A/TMS9928A/TMS9929A Video Display Processors Data Manual*, Texas Instruments, November 1982. 105 pages, 6,785,534 bytes, SHA-256 `3991f0c691b83036bbb96d8e60e8d4ed4cfbb5eed9567ad61737570771113450`. It is not redistributable and is not carried here. `python3 -m conformance.documents` brings it down from https://bitsavers.org/components/ti/TMS9900/TMS9918A_TMS9928A_TMS9929A_Video_Display_Processors_Data_Manual_Nov82.pdf and refuses any other file.
- openMSX, `src/video/VDPAccessSlots.cc` and `src/video/VDP.hh` at commit `99c28389d775b945c57be27df1def0925e28abd8`, https://github.com/openMSX/openMSX, for the window positions. Facts only; no code is taken.
- MAME, `src/devices/video/tms9928a.cpp` at commit `dc00cf3517eef30587b33efbf1e1c63ad3531b58`, https://github.com/mamedev/mame, for behaviour neither the manual nor openMSX covers. Facts only; no code is taken.

## Citing this

[CITATION.cff](CITATION.cff) is kept in step with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
