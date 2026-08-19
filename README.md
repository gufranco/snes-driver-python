<div align="center">

<h1>SNES Driver</h1>

<strong>What a cartridge says to its coprocessor, read out of the cartridge's own code.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml)
[![Cartridges](https://img.shields.io/badge/read%20across-36%20cartridges-blue)](#what-real-cartridges-say)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#tests)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
  <a href="#the-problem">The problem</a> &nbsp;|&nbsp;
  <a href="#quick-start">Quick start</a> &nbsp;|&nbsp;
  <a href="#what-real-cartridges-say">What cartridges say</a> &nbsp;|&nbsp;
  <a href="#why-this-cannot-be-guessed">Why guessing fails</a> &nbsp;|&nbsp;
  <a href="https://github.com/gufranco/snes-driver-python/issues">Issues</a>
</p>

**36** cartridges read · **2** layouts · **3** kinds of access · **110** tests · **100%** statement and branch coverage

```python
from snesdriver import shapes, window_for

shapes(open("Super Mario Kart (USA).sfc", "rb").read(), window_for("dsp", "hirom"))
# {'write1 write2 write2 poll2 read2 read2': 2, ...}
```

---

## The problem

A SNES coprocessor tells the console almost nothing. There is a data register and a status register, and how many bytes a command takes and how many it gives back is not something the part can be asked. It is knowledge the cartridge has and the console does not.

That matters because a model of the part needs those numbers. Get them from a datasheet and you are fine, except most of these parts have no surviving datasheet. Get them by trying things and you learn about the commands you thought to try.

There is one place the protocol is written down exactly: the routine the cartridge runs to drive the part. It was written by somebody with the part on a desk who had to make it work. So this reads that.

## Why this cannot be guessed

The obvious idea is to watch the part's ready bit and let it tell you when an answer is waiting. Measured on the DSP-1, that bit stays asserted through the whole exchange, so watching it tells you nothing.

The cartridges do poll, but they poll the **status register** at the other address, and only at the points their own protocol requires. That is visible in what they run and in nothing else:

```text
Super Mario Kart   write1 write2 poll2 read2 read2 read2 read2 poll2 write2 ...
Pilotwings         poll1 write1 write2 write2 write2 read2 read2 write1 ...
Dungeon Master     write1 write1 write1 write1 write1 read1 read1 read1 read1
```

One byte of command, argument words, a poll, then answer words. That shape is the thing a model has to be told, and no amount of poking the part from outside recovers it.

## Quick start

### Prerequisites

| Tool | Version | Install |
|:-----|:--------|:--------|
| Python | >= 3.12 | [python.org](https://www.python.org/downloads/) |
| git | any | submodules carry the disassembler and the memory map |

### Setup

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-driver-python.git
cd snes-driver-python
```

### Run

Put copies you already own in [`cartridges/`](cartridges/), keeping the filenames in [`cartridges/README.md`](cartridges/README.md), then:

```bash
python3 conformance/against_cartridges.py
```

Point `SNES_CARTRIDGE_DIR` at a library somewhere else to read from there instead.

## What real cartridges say

Read across the 36 DSP cartridges on hand:

| Cartridge | Layout | Sites | Distinct shapes |
|:----------|:-------|------:|----------------:|
| Super Mario Kart | hirom | 122 | 13 |
| Pilotwings | lorom | 122 | 17 |
| Dungeon Master | lorom | 130 | 13 |

A **site** is one instruction that reaches the part. A **shape** is one routine's whole exchange. Those differ because a routine that writes and then reads is one exchange rather than two, so a site an earlier walk already stepped over does not start a conversation of its own. Reporting the tail of a routine as though it were the whole thing is the mistake that makes this look easier than it is.

## How it reads

Nothing is executed. A routine is walked straight through, from its first instruction to the first one that leaves, and every instruction is asked what it reached.

The part that cannot be skipped is width. A store to a coprocessor moves one byte or two depending on the accumulator, and the accumulator's width is not in the instruction: a `sep` or a `rep` set it earlier. A walk that ignores those reads every access at the wrong size and reports an exchange the console never had.

Which register an access lands on is decided by the layout, not by the part. The same DSP answers at `$30-3F:8000` in a low cartridge and `$00-0F:6000` in a high one, and the line that picks between data and status is address bit 14 in the first case and bit 12 in the second.

## Bringing your own cartridges

Every cartridge is confirmed against four digests before a byte of it is disassembled. `sha256` decides; the other three are confirmed too, because a file can be the right length under the right name and still be a bad dump.

That check is not ceremony here. A file that is not the one named would be disassembled anyway and would report a protocol nobody's hardware has, which is worse than reporting nothing. Every filename and all four digests are printed in [`cartridges/README.md`](cartridges/README.md) so a copy can be checked before it is supplied.

Nothing in that directory is shared, and no part of any cartridge is reconstructible from anything here.

## Tests

```bash
for f in snesdriver/*.test.py conformance/*.test.py; do python3 "$f"; done
```

| Suite | File | Covers |
|:------|:-----|:-------|
| Windows | [`snesdriver/windows.test.py`](snesdriver/windows.test.py) | Where each part answers under each layout |
| Walk | [`snesdriver/walk.test.py`](snesdriver/walk.test.py) | Accumulator width, where a routine ends, what each instruction reached |
| Conversation | [`snesdriver/conversation.test.py`](snesdriver/conversation.test.py) | Writes, reads, polls, shapes, and counting a routine once |
| Cartridges | [`conformance/cartridges.test.py`](conformance/cartridges.test.py) | The manifest and all four digests |
| Sweep | [`conformance/against_cartridges.test.py`](conformance/against_cartridges.test.py) | Every cartridge present, read |

The last one is skipped rather than passed when no cartridge is present, so a run that proved nothing never reads as a run that proved something. CI attempts it on every push and annotates the skip.

## Built on

| Package | Does |
|:--------|:-----|
| [`mos65xx`](https://github.com/gufranco/mos65xx-python) | Disassembles the 65816, which is what a driver routine is written in |
| [`snes-mapper`](https://github.com/gufranco/snes-mapper-python) | Decides which layout a cartridge declares |

## Licence

MIT. See [`LICENSE`](LICENSE).
