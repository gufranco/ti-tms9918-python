# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this
family carries, byte for byte, and it decides most questions before they are
asked. What follows is only what is true of this member. [README.md](README.md)
is the document written for a person.

## What this project is, in one paragraph

A model of the Texas Instruments TMS9918A, TMS9928A and TMS9929A video display
processors, advanced one master clock tick at a time. It covers the port
protocol, the registers and status, the four display modes and the four
undocumented mode combinations, the sprite rules, and the line and frame timing
of all three parts. It also models when each video memory access the processor
asks for actually lands. What the manual prints comes from TI's 1982 data
manual. What it does not print comes from openMSX and MAME, marked unverified.
What real software asks of the part comes from a census over the SG-1000
library.

## The interface a caller drives

- `tms9918.Chip(model, memory)` builds a part. `model` is one of `tms9918a`,
  `tms9928a` or `tms9929a`. `memory` is a `Vram`, and the part builds its own
  when it is left out. Everything comes up scrambled, so call `reset()` and read
  the status once, as real software does, before programming registers.
- `write_control`, `write_data`, `read_data` and `read_status` are the four port
  operations.
- `tick()` advances one master clock period and returns the CPUCLK and GROMCLK
  edges on the TMS9918A. `clock()` advances one dot, which is two ticks.
- After each dot, `region` and `colour` describe it. `interrupt` is the INT pin,
  true while it is asserted.

Everything the package raises lives in
[`tms9918/errors.py`](tms9918/errors.py) and nowhere else.

This is a part, not a clocked part in the family's sense. It runs no program, so
it has no `step`, and it is built by `Chip`.

## The authority ladder

1. **[`conformance/hardware.json`](conformance/hardware.json) facts**, quoted
   from TI's data manual and matched against its text layer by
   [`conformance/quotes.py`](conformance/quotes.py). Its tables were also read
   from the page image.
2. **The SG-1000 library**, through
   [`conformance/census.py`](conformance/census.py), for what real software
   reaches.
3. **openMSX** for where the processor's windows fall, and **MAME** for what
   neither covers, each under `notStated` with `verified: false`.

[`conformance/divergences.json`](conformance/divergences.json) records every
place two sources part, including the places the manual contradicts itself.

## What is settled and what is not

**Settled: everything the manual prints and a test can reach.** Each fact in
[`conformance/hardware.json`](conformance/hardware.json) names, under `heldBy`,
the tests that hold it:
[`conformance/hardware.test.py`](conformance/hardware.test.py) for the ports,
status and timing, and
[`conformance/display.test.py`](conformance/display.test.py) for the tables,
colours and sprites.

**Settled: every bound the manual prints on access time holds over the window
table.** [`tms9918/slots.test.py`](tms9918/slots.test.py) checks it.

**Not settled: 21 things**, every entry under `notStated` and two
places the manual contradicts itself, each in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with what would close it. Do not close one
by argument.

## The windows are openMSX's, and the bounds are TI's

The manual says how often the processor gets a window and how long an access can
wait. It never says which dot a window falls on. The positions in
[`tms9918/slots.py`](tms9918/slots.py) are openMSX's MSX1 positions, restated
in this package's master ticks from the start of the active line and built from
their strides. openMSX's tables are not carried, only the positions they give.
Every bound TI printed is a test over them.

**If you are about to change a window, a lead time or a fetch position, run the
census before and after.** A moved count of lost accesses means the windows moved.
[`tms9918/slots.test.py`](tms9918/slots.test.py) also holds the model to the
measured threshold: 26 processor cycles between writes can lose one, and 27
never does.

## Three machine names are exempt, and only three

The TMS9918A was a catalogue part, so no tracked file names a machine it shipped
in, and [`conformance/family.test.py`](conformance/family.test.py) holds the
list it sweeps for. The SG-1000 and the SC-3000 are named because their library
is the census's oracle. The MSX is named because openMSX's cited measurements
were taken on one. Any other mention names the part by its number.

## Every gate, in the order to run them

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
uvx yamllint==1.38.0 --strict .
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for f in $(find tms9918 conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$f" || echo "FAILED $f"
done
"${cov[@]}" report
```

Then the ones outside the coverage step:

```bash
python3 -m conformance.corpus
python3 -m conformance.speed
python3 -m conformance.documents
python3 -m conformance.quotes
```

And, with an SG-1000 library present, the one that walks it:

```bash
python3 -m conformance.census <library> [library ...] [--frames N] [--jobs N]
```

Everything under [`conformance/`](conformance) runs as a module. Run as a
script, its own directory goes on the import path and a file there shadows any
standard library module of the same name.

## Conventions that are not negotiable

| Thing | Rule |
|:------|:-----|
| Language | Python only |
| Comments | None in source or in build files, and a docstring counts as one. Names, small functions, constants and types carry what a comment would have said |
| Test layout | `<module>.test.py` beside the module it covers |
| Test shape | Arrange, act, assert, each opened by its bare marker |
| Coverage | 100% statements and branches, enforced |
| Types | `mypy` at strict, plus every optional error class |
| Package manager for tooling | pnpm, never npm |
| Commits | Conventional Commits, subject at most 50 characters |
| Documents | Read, quoted and pinned by digest. Never committed |
| Cartridges | Never committed, in any form, for any reason |

The linter's ignores in [`pyproject.toml`](pyproject.toml) carry no comments, so
their reasons live here:

- `N818`: some exceptions are signals rather than failures. The standard
  library names those without the suffix too.
- `N999` and `PLR2004` in tests: a test file is named after its module with a
  dot, and its literals are the expected values.
- `T201` in `conformance/`, the doctor and `environment.py`: printing is their
  output.
- `BLE001` in the doctor, `environment.py` and the census: a check that throws
  has to become a line in the report rather than end the run. One image that
  raises must not throw away the census's results for every other image.
- The `z80.*` override in mypy: the submodule is checked in its own repository,
  against its own gate.

## Layout

```
tms9918/
  core.py        the part: ports, the access engine, timing, display and status
  models.py      the three parts and what differs between them
  geometry.py    Table 3-3 laid out dot by dot and line by line
  slots.py       where the processor's windows fall, from openMSX
  patterns.py    the display modes, one cell at a time
  sprites.py     sprite evaluation and one line of sprite dots
  levels.py      Table 2-3, as printed
  memory.py      the 16K of video memory, scrambled at power on
  errors.py      everything this package raises
  doctor.py      what the machine and the package look like, for a report
  environment.py what the doctor reads about the machine
  version.py     rewritten by the release job and by nothing else
conformance/
  census.py         boots every SG-1000 image in a library you own and counts what it reaches
  harness.py        the SG-1000 board the census boots it on
  bench.py          the record and a reset part, shared by the record's tests
  cartridges.py     where each cartridge board puts its own RAM
  boards.json       which images carry RAM, by whole-file SHA-1, from MAME's software list
  corpus.json       those counts, holding nothing from any cartridge
  corpus.py         replays them
  documents.json    the manual, by digest
  documents.py      brings it down and refuses any other file
  hardware.json     TI's manual, fact by fact, and every value it does not print
  divergences.json  every place two sources part
  manual.py         the manual's text, flattened to letters and digits
  quotes.py         every quote the records carry, found in the manual
  links.py          the weekly check that every cited address still answers
  speed.py          the throughput floor
  package.py        the wheel audit
  source.py         the check that no documentation string remains
  family.test.py    the family standard, held as tests
zilog-z80-python/   the processor the census drives, a pinned submodule
```

## Things that will bite you

**The latch comes up scrambled.** A part straight out of `reset()` may take your
first control byte as the second half of a pair. Read the status first, which is
what every real program does and what clears the latch.

**`clock()` reports the dot it just finished.** After it returns, `region` and
`colour` describe that dot, and `line` and `dot` already name the next one.

**The frame flag rises as line 192 begins.** A loop waiting for it by line
number has to wait for the line after 191, not for 191.

**Text mode's area starts six dots later than the others.** Horizontal sync is
on the same dots in every mode, so the shorter text area sits inside the same
line.

## Before calling anything finished

[`FAMILY.md`](FAMILY.md) carries a checklist under "What a new repository has to
have before it is a member". Every line on it was a defect found in one of these
repositories and fixed in all of them. Read it before adding a surface, and read
it again before saying a change is done.

**A check nobody has seen fail is not known to work.** Drive it, once,
deliberately, against input that should fail it.

**Silence and success produce the same output.** A census that walked no file
says so, and exits non-zero.

## What a change is expected to leave behind

A gate that would have caught the bug. A change to timing, the windows or a
display mode also runs the census over a real library. The tests check what the
manual says. The census checks what software that ran on the chip still does.
