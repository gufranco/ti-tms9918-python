# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful is still a claim rather than a
measurement. The authority above everything else is TI's 1982 data manual,
read twice. Below it sit openMSX and MAME, which are leads rather than
authorities, and an SG-1000 library, which says what software reaches but not
what the chip does with it.

Every entry is also in [`conformance/hardware.json`](conformance/hardware.json)
under `notStated`, or in [`conformance/divergences.json`](conformance/divergences.json),
so a program can read what a person reads here.

## What would settle almost all of them

A logic analyser on RAS, CAS, R/W, CSW, CSR and INT of a running TMS9918A or
TMS9928A, triggered on horizontal sync, while a test program writes and reads
video memory in each mode. One capture places every window, every fetch and
the frame flag. A TMS9929A board settles its border split the same way.

## What the manual does not print

### Which dot each processor window falls on

**This package does.** The positions in slots.py, from openMSX's MSX1 tables.

**Why it is open.** The manual bounds how long an access waits and how often windows come, but never says which dot each window is on.

**Where the value came from.** openMSX src/video/VDPAccessSlots.cc at 99c28389d775b945c57be27df1def0925e28abd8, the MSX1 tables, which its comments say were measured on MSX1 hardware. No second independent source exists, because MAME does not model windows.

**What would settle it.** A logic analyser on RAS, CAS and R/W of a running TMS9918A or TMS9928A, triggered on horizontal sync, with the processor writing continuously in each mode.

### How long after a port access the first usable window is

**This package does.** 16 master ticks, about 1.49 microseconds.

**Why it is open.** The manual says about 2 microseconds after address setup, which is 21 master ticks, without placing it against the windows.

**Where the value came from.** openMSX VDP.cc, scheduleTMS99x8VramAccess, which records a measurement on a real MSX in Screen 2 with sprites: data writes 26 processor cycles apart or fewer corrupt video memory, and 27 or more never do. With openMSX's window positions only a lead of 8 TMS cycles, 16 master ticks or 1.49 microseconds, reproduces both halves. openMSX itself ships 7 cycles because Chase HQ corrupted at 8; see divergences.json.

**What would settle it.** The same logic analyser capture, measuring from the rising edge of CSW to the next CAS that carries the data.

### On which line the window pattern changes

**This package does.** From 636 master ticks into the second line before the first active one, which is openMSX's 162 cycles into the line before its display area, until 636 ticks into the last active line.

**Why it is open.** The manual does not say when the window pattern changes between the border and the display.

**Where the value came from.** openMSX VDP.hh, isSlotTableDisplayEnabled, measured on the V99x8 and applied to the MSX1 tables by openMSX.

**What would settle it.** The logic analyser capture across the first and last active lines.

### What a second access does to one still waiting

**This package does.** Replaces the first.

**Why it is open.** The manual warns against accessing faster than the window allows but does not say what happens.

**Where the value came from.** openMSX describes a single request buffer; this package lets the later request take it.

**What would settle it.** Two data writes closer together than a window, then the bytes at both addresses read back.

### What the address register does between the two control bytes

**This package does.** The first control byte goes straight into the address's low byte, any data access or status read clears the latch, and a register write also loads the address's high byte.

**Why it is open.** The manual specifies the byte order of the two-byte writes, not what the register does between them.

**Where the value came from.** MAME tms9928a.cpp at dc00cf3517eef30587b33efbf1e1c63ad3531b58, register_write and the data and status paths.

**What would settle it.** Write one control byte, then read data, then write one control byte and a register number, and read the address back through a data read.

### Whether a data write loads the read buffer

**This package does.** A data write also loads the read buffer.

**Why it is open.** Not stated.

**Where the value came from.** MAME vram_write.

**What would settle it.** Write a byte, then read data without a new setup, and compare with the byte written.

### Which register a number above 7 selects

**This package does.** The low three bits of the second byte.

**Why it is open.** The manual says the four bits after the leading 1 must be 0, not what happens when they are not.

**Where the value came from.** MAME register_write, data & 7.

**What would settle it.** Write register numbers 8 to 15 and see which registers change.

### What the low bits of registers 3 and 4 do in Graphics II

**This package does.** The low bits of registers 3 and 4 act as AND masks on the name and third.

**Why it is open.** The manual requires those bits to be 1 and does not say what other values do. With them all 1 the masks change nothing, which is the documented case.

**Where the value came from.** MAME update_table_masks.

**What would settle it.** Graphics II with register 3 at 0x9F and register 4 at 0x00, then a frame captured and compared with the table contents.

### What the four undocumented mode combinations draw

**This package does.** Text with multicolor and all three bits draw four dots on and two off; text with Graphics II reads the masked thirds; Graphics II with multicolor reads multicolor colours through the thirds.

**Why it is open.** The mode table on page 2-5 lists four combinations of three bits.

**Where the value came from.** MAME update_line, modes 3, 5, 6 and 7. For Graphics II with multicolor MAME adds the row to the name before shifting, which this package does not follow; see divergences.json.

**What would settle it.** Each combination set on hardware and a frame captured.

### How a size 1 sprite forms its pattern address

**This package does.** The low two bits of the name are ignored.

**Why it is open.** The manual says only that the address formation is slightly modified for SIZE 1 sprites.

**Where the value came from.** MAME update_line, sprcode & ~0x03.

**What would settle it.** A size 1 sprite named 1 and one named 4 shown side by side.

### What the fifth-sprite bits hold when the flag is clear

**This package does.** The last plane examined, or 31 when the scan runs to the end.

**Why it is open.** The manual says the number is valid whenever the flag is set, not what the bits hold otherwise.

**Where the value came from.** MAME update_line, m_FifthSprite.

**What would settle it.** Status reads on frames with no fifth sprite and terminators at known planes.

### When the sprites for a line are read

**This package does.** Dot 256 of the line before.

**Why it is open.** The manual does not say when sprites for a line are read.

**Where the value came from.** openMSX notes the sprite fetch for the first display line starts in the line before it; the dot is this package's choice.

**What would settle it.** Change a sprite's position at known dots in the line before and capture which line shows it.

### When the name, pattern and colour bytes for a cell are read

**This package does.** When the cell's first dot is shown.

**Why it is open.** The manual does not place the name, pattern and colour reads.

**Where the value came from.** This package's choice; neither implementation models it.

**What would settle it.** The logic analyser capture, reading which address follows each CAS.

### On which dot the frame flag rises

**This package does.** The first dot after line 191.

**Why it is open.** The manual places it at the end of the last active line, not on a dot.

**Where the value came from.** This package reads the manual's sentence literally. MAME sets it at the end of the following line; see divergences.json.

**What would settle it.** INT captured against horizontal sync.

### Where reset leaves the counters

**This package does.** The first line of top blanking, dot 0.

**Why it is open.** The manual says known states without naming them.

**Where the value came from.** MAME device_reset, which starts its line timer at the top of the blanking.

**What would settle it.** Release RESET and time the first INT.

### How the TMS9929A divides its border between top and bottom

**This package does.** 51 lines above the display and 51 below it.

**Why it is open.** Figure 5-13 gives the TMS9929A 294 lines of border and display without dividing the border.

**Where the value came from.** MAME VERT_DISPLAY_START_PAL, 13 + 51.

**What would settle it.** A TMS9929A frame captured with a distinct backdrop, counting lines above and below the display.

### Whether sprites are processed while the display is blanked

**This package does.** No sprite processing and no flag changes.

**Why it is open.** Not stated.

**Where the value came from.** MAME update_line, which skips sprites when the BLANK bit is clear.

**What would settle it.** Five sprites on a line with the display blanked, then a status read.

### What the 4/16K bit does to a 16K board

**This package does.** The 4/16K bit is held and changes no address.

**Why it is open.** The manual describes how the two RAM types are wired, not how a 16K RAM behaves with the bit clear.

**Where the value came from.** MAME lists it as unmodelled.

**What would settle it.** A 16K board run with the bit clear, reading back a pattern written across the whole RAM.

### Whether a status read clears the fifth-sprite number

**This package does.** Kept.

**Why it is open.** The manual says a status read clears F, C and 5S, not the number.

**Where the value came from.** MAME register_read, which leaves the number in place.

**What would settle it.** Two status reads after a fifth sprite.

## Where the manual contradicts itself

### Whether sprite dots outside the active area set the coincidence flag

**The manual says.** Page 2-11 says sprites partly or wholly off the screen are considered. Page 2-16 says only sprites active on the display set the flag.

**This package does.** Counts coincidence only on the 256 active dots. Page 2-11 also says the check happens during the generation of the pixel, and no pixel is generated off the screen. MAME counts the same way.

**What would settle it.** Two sprites overlapping only in the dots past the right edge of the active area on hardware, and a status read.

### The colour burst R-Y level on the colour-difference parts

**The manual says.** Table 2-3 prints 47(28A) and 73(29A) with no decimal point, beside .1(28A) and .2(29A) for B-Y.

**This package does.** Reads them as .47 and .73. Every other entry in the column is a fraction of the white-black swing, and .47 is the column's no-colour level.

**What would settle it.** Another printing of the manual, or the burst measured on a TMS9928A.
