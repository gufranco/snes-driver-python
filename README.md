# SNES Driver

Reads the 65816 routine a SNES cartridge runs to drive its coprocessor and reports every access it makes to the part, held to the driver code of the cartridges its manifest names.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-driver-python)](https://github.com/gufranco/snes-driver-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**42** cartridges named by four digests, **36** DSP cartridges read under **2** layouts, **0** disagreements with their own digests, **0** that said nothing to the part, **3** kinds of access, **668** tests, **100%** statement and branch coverage, no dependencies

```python
from snesdriver import at, window_for

routine = bytes(
    [0xE2, 0x20, 0xA9, 0x01, 0x8F, 0x00, 0x60, 0x00]
    + [0xC2, 0x20, 0xAF, 0x00, 0x70, 0x00, 0xAF, 0x00, 0x60, 0x00, 0x60]
)

print(at(routine + bytes(2048), 0, window_for("dsp", "hirom")).shape)
```

```
write1 poll2 read2
```

The routine sets the accumulator to 8 bits, stores one byte at `$00:6000`, sets it back to 16 bits, loads a word from `$00:7000` and a word from `$00:6000`, and returns. Under a high cartridge layout the DSP's data register answers at `$6000` and its status register at `$7000`. So the exchange is one byte of command, a poll of the status register, and a two byte answer. Nothing was executed: each instruction was disassembled and asked what it reached.

## Install

| Requirement | Version |
|:--|:--|
| Python | 3.12 or newer |
| git | Any, to fetch the two submodules |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-driver-python.git
cd snes-driver-python
python3 snesdriver/doctor.py
```

The package imports nothing outside the standard library and its two submodules. [`mos65xx-python`](https://github.com/gufranco/mos65xx-python) disassembles the 65816, and [`snes-mapper-python`](https://github.com/gufranco/snes-mapper-python) resolves an address under a cartridge layout. The download-zip link on the repository page gives a checkout without either, and that checkout fails at import. In a checkout made without `--recurse-submodules`, run `git submodule update --init --recursive`.

The package is not on a package index, and [`pyproject.toml`](pyproject.toml) carries no `[project]` block. A wheel could not carry the submodules, so it would install and then fail on its first import.

The doctor checks the machine, the submodules, the manifest and the cartridge library, and ends with one line. It exits 0 when every check passes and 1 when one does not. Paste its whole output into any bug report.

```
  16 checks, nothing to report
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/snes-driver-python/releases).

## The interface

Every call takes the bytes of a cartridge image and returns what its code reaches. There is no clock, no state and no model of a part.

### Where a part answers

| Name | Content |
|:--|:--|
| `window_for(part, layout)` | The `Window` that part answers in under that layout, or `None` when it has none there. Raises `UnknownPart` for a part name `WINDOWS` does not hold |
| `WINDOWS` | Every window, keyed by part and then by layout |
| `Window(first_bank, last_bank, data, status, end, status_end=None)` | One window. `status_end` defaults to `end` |
| `window.reaches(bank, address)` | `DATA`, `STATUS` or `None` for one address. The status range is tested first |
| `busiest(layout, reaches)` | The part whose window under `layout` holds the most of the `(bank, address)` pairs in `reaches`, or `None` when no window holds any |
| `DATA`, `STATUS` | The strings `"data"` and `"status"` |
| `UnknownPart` | Raised by `window_for`. The message lists every part there is |

| Part | Layout | Banks | Data | Status | Data ends | Status ends |
|:--|:--|:--|:--|:--|:--|:--|
| `dsp` | `lorom` | `$30-$3F` | `$8000` | `$C000` | `$FFFF` | `$FFFF` |
| `dsp` | `hirom` | `$00-$0F` | `$6000` | `$7000` | `$7FFF` | `$7FFF` |
| `st` | `lorom` | `$60-$67` | `$0000` | `$0001` | `$0001` | `$0001` |
| `st` | `lorom-shared` | `$68-$6F` | `$0000` | `$0020` | `$0FFF` | `$0021` |
| `obc1` | `lorom` | `$00-$3F` | `$6000` | `$7FF0` | `$7FFF` | `$7FFF` |
| `st018` | `lorom` | `$00-$3F` | `$3800` | `$3804` | `$3803` | `$3804` |

```python
import snesdriver

for part, layouts in sorted(snesdriver.WINDOWS.items()):
    for layout, window in sorted(layouts.items()):
        print(part, layout, window)

high = snesdriver.window_for("dsp", "hirom")
print(high.reaches(0x00, 0x6000), high.reaches(0x00, 0x7000), high.reaches(0x10, 0x6000))
print(snesdriver.window_for("obc1", "hirom"))
print(snesdriver.busiest("lorom", [(0x30, 0x8000), (0x30, 0xC000), (0x60, 0x0000)]))

try:
    snesdriver.window_for("sa1", "lorom")
except snesdriver.UnknownPart as error:
    print(error)
```

```
dsp hirom <Window $00-$0f:6000 data, 7000 status>
dsp lorom <Window $30-$3f:8000 data, c000 status>
obc1 lorom <Window $00-$3f:6000 data, 7ff0 status>
st lorom <Window $60-$67:0000 data, 0001 status>
st lorom-shared <Window $68-$6f:0000 data, 0020 status>
st018 lorom <Window $00-$3f:3800 data, 3804 status>
data status None
None
dsp
sa1 is not a part with a known window; there are dsp, obc1, st, st018
```

`window_for` returns `None` for a part that exists and has no window under the layout asked about, and raises for a name no part goes by. `busiest` counts two addresses in the `dsp` window and one in the `st` window, so it names `dsp`.

### Walking a routine

`through(rom, offset, narrow=True, limit=DEFAULT_LIMIT, address=None, bank=None, depth=8)` disassembles one routine from `offset` and yields a `Step` per instruction.

| Argument | Meaning |
|:--|:--|
| `rom` | The image as bytes |
| `offset` | File offset of the first instruction |
| `narrow` | The accumulator width at entry: `True` for 8 bits, `False` for 16 |
| `limit` | The most instructions walked in the routine itself. `DEFAULT_LIMIT` is 80. Instructions inside a callee do not count, and the whole walk stops at 16 times `limit` |
| `address` | The CPU address of `offset`. Defaults to `$8000` plus `offset` modulo `$8000` |
| `bank` | The bank the routine runs in. Defaults to `offset` divided by `$8000` |
| `depth` | How many calls deep the walk follows `jsr` and `jsl` |

The walk ends at the first `rts`, `rtl`, `rti`, `jmp`, `jml`, `bra`, `brl` or `stp` in the routine itself. A `sep` or `rep` that names the accumulator bit changes the width of every access after it. A call is followed only when its target walks to a `rts` or `rtl` within 200 instructions; any other call is stepped over.

| `Step` attribute | Meaning |
|:--|:--|
| `offset` | File offset of the instruction |
| `mnemonic` | Lower case, such as `sta` |
| `width` | 1 or 2, the bytes an accumulator access moves |
| `narrow` | True when `width` is 1 |
| `depth` | 0 in the routine itself, 1 inside a call from it, and so on |
| `bank` | The bank an absolute or long access reaches, otherwise `None` |
| `address` | The 16-bit address an absolute or long access reaches, otherwise `None`. `pea` and `per` reach nothing |
| `banked` | True for a long access, whose bank is spelled in the instruction. An absolute access takes the routine's own bank instead |
| `reading` | False for a mnemonic starting with `st`, otherwise True |
| `immediate` | The operand of an immediate instruction, otherwise `None` |
| `waiting` | True for a branch backwards, which is how a routine waits on a register |

```python
from snesdriver import through

routine = bytes(
    [0xE2, 0x20, 0xA9, 0x01, 0x8F, 0x00, 0x60, 0x00, 0xC2, 0x20, 0x8F, 0x00, 0x60, 0x00, 0x60]
)

for step in through(routine + bytes(2048), 0):
    where = "-" if step.address is None else f"${step.bank:02x}:{step.address:04x}"
    print(f"{step.offset:#06x} {step.mnemonic} {step.width} {where} {step.banked}")
```

```
0x0000 sep 1 - False
0x0002 lda 1 - False
0x0004 sta 1 $00:6000 True
0x0008 rep 1 - False
0x000a sta 2 $00:6000 True
0x000e rts 2 - False
```

The two stores are the same four bytes. The first moves one byte because the `sep #$20` before it narrowed the accumulator, and the second moves two because the `rep #$20` widened it again.

### Reading the exchange

`at(rom, offset, window, narrow=True, limit=DEFAULT_LIMIT)` walks one routine with `through` and returns a `Conversation` holding every access that reached `window`.

| Kind | Constant | An access is this kind when |
|:--|:--|:--|
| `write` | `WRITE` | It stores to the data or the status register |
| `read` | `READ` | It loads from the data register |
| `poll` | `POLL` | It loads from the status register |

| `Conversation` attribute | Meaning |
|:--|:--|
| `shape` | Each access as its kind followed by its width, joined by spaces |
| `steps` | One record per access, with `what`, `width`, `bank`, `address`, `banked` and `whole`, the 24-bit address |
| `covered` | File offsets of every instruction walked in the routine itself |
| `written` | Bytes written |
| `read` | Bytes read from the data register |
| `polls` | True when the routine polls at least once |
| `banked` | True when every access spelled its own bank |

A `Conversation` is false when nothing reached the window.

```python
from snesdriver import at, shapes, sites, window_for

routine = bytes(
    [0xE2, 0x20, 0xA9, 0x01, 0x8F, 0x00, 0x60, 0x00]
    + [0xC2, 0x20, 0xAF, 0x00, 0x70, 0x00, 0xAF, 0x00, 0x60, 0x00, 0x60]
)
image = routine + bytes(2048)
window = window_for("dsp", "hirom")

talk = at(image, 0, window)
print(talk, talk.written, talk.read, talk.polls, talk.banked)
print(talk.steps)
print(sorted(talk.covered))
print([f"{one:#06x}" for one in sites(image, window)])
print(shapes(image, window))
```

```
<Conversation write1 poll2 read2> 1 2 True True
(<write 1>, <poll 2>, <read 2>)
[0, 2, 4, 8, 10, 14, 18]
['0x0004', '0x000a', '0x000e']
{'write1 poll2 read2': 1}
```

The routine has three sites and one shape. The walk from the first site covers the other two, so they do not start conversations of their own.

### Finding every routine

| Call | Returns |
|:--|:--|
| `sites(rom, window)` | File offsets of every long load, opcode `$AF`, and long store, opcode `$8F`, whose address reaches `window`. A byte search: it also finds those four bytes inside data |
| `reached(rom, window, entry=None, kind="lorom")` | File offsets of every instruction that reaches `window` on a walk from the ten native and emulation vectors, or from `entry`, following every call, jump and branch whose destination is spelled in the instruction. `kind` is the layout that maps addresses to file offsets. The walk stops after 400,000 instructions |
| `shapes(rom, window, narrow=True, limit=DEFAULT_LIMIT, find=sites)` | Every distinct shape and how many routines produce it. Each offset `find` returns starts a walk with `at` unless an earlier walk covered it |

```python
from snesdriver import reached, shapes, sites, window_for

routine = bytes([0xE2, 0x20, 0xA9, 0x01, 0x8F, 0x00, 0x80, 0x30, 0xAF, 0x00, 0xC0, 0x30, 0x60])
image = bytearray(0x8000)
image[: len(routine)] = routine
image[0x0100:0x0104] = bytes([0x8F, 0x00, 0x80, 0x30])
image[0x7FFC:0x7FFE] = (0x8000).to_bytes(2, "little")
image = bytes(image)
window = window_for("dsp", "lorom")

print([f"{one:#06x}" for one in sites(image, window)])
print([f"{one:#06x}" for one in reached(image, window)])
print(shapes(image, window))
print(shapes(image, window, find=reached))
```

```
['0x0004', '0x0008', '0x0100']
['0x0004', '0x0008']
{'write1 poll1': 1, 'write1': 1}
{'write1 poll1': 1}
```

The image is one low cartridge bank whose reset vector points at the routine. The four bytes at `$0100` spell a long store to the DSP and are never executed. `sites` finds them, and `reached` does not, because no walk from a vector arrives there.

### Module contents

| Name | Content |
|:--|:--|
| `snesdriver.DEFAULT_LIMIT` | 80, the default `limit` of `through`, `at` and `shapes` |
| `snesdriver.VERSION`, `snesdriver.__version__` | The installed version |
| `snesdriver.walk.Step` | The class `through` yields |
| `snesdriver.conversation.Step` | The class of each entry in `Conversation.steps` |

### Commands

| Command | Arguments | Exit codes |
|:--|:--|:--|
| `python3 snesdriver/doctor.py` | None | 0 every check passed, 1 one did not |
| `python3 -m conformance.against_cartridges` | An optional directory to read instead of the default | 0 every cartridge spoke to the DSP, 1 one said nothing, 2 no cartridge was found |
| `python3 -m conformance.speed` | None | 0 the walk beat the floor of 20,000 routines walked per second, 1 it did not |
| `python3 -m conformance.links` | None | 1 when an address in this file answers HTTP 404 or 410, otherwise 0 |

## Why this cannot be guessed

A SNES coprocessor shows the console a data register and a status register. How many bytes a command takes and how many it returns is not something the part can be asked. Most of these parts have no surviving datasheet. The routine the cartridge runs to drive the part is the one place the protocol is written down, and this package reads that routine.

The cartridges poll the status register only at the points their own protocol requires. The start of one shape from each of three cartridges, as `shapes` reports it:

```text
Super Mario Kart   write1 write2 poll2 read2 read2 read2 read2 poll2 write2 ...
Pilotwings         poll1 write1 write2 write2 write2 read2 read2 write1 ...
Dungeon Master     write1 write1 write1 write1 write1 read1 read1 read1 read1
```

## How it reads

A routine is walked from its first instruction to the first one that leaves, and each instruction is asked what it reached. Width cannot be skipped. A store moves one byte or two depending on the accumulator, and the accumulator's width is set by an earlier `sep` or `rep`, not by the store. A walk that ignored them would report every access at the wrong size.

The layout decides which register an access lands on. The DSP answers at `$30-$3F:8000` in a low cartridge and at `$00-$0F:6000` in a high one. The address line that picks the status register is bit 14 in the first case and bit 12 in the second.

## Bringing your own cartridges

Every cartridge is identified by its `sha256` and then confirmed against its `crc32`, `md5` and `sha1` before a byte of it is disassembled. A file whose `sha256` matches and whose other digests do not stops the sweep with an error. A file the manifest does not know is skipped. Called on such a file directly, `conformance.cartridges.identify` names the likely cause: a copier header, swapped bytes, a known bad dump or a modified release.

Put copies you own in [`cartridges/`](cartridges/README.md), in a `cartridges` directory beside this repository, or wherever `SNES_CARTRIDGE_DIR` points. When the variable is unset the sibling directory is tried first. [`cartridges/README.md`](cartridges/README.md) lists every filename and all four digests, and [`cartridges.manifest.json`](cartridges.manifest.json) holds the same in a form a program reads. Nothing in the repository reconstructs any part of a cartridge.

## What each piece of evidence is worth

| Evidence | What it settles | What it cannot |
|:--|:--|:--|
| The cartridge's own code, walked instruction by instruction | What a shipped game sends to the part | Anything no game sends |
| The 65816 instruction set, through the disassembler | What each instruction is and how wide its access is | Anything about the part on the other end |
| The layout the header declares, through the mapper | Which addresses reach the part | What happens when they do |
| Four digests of every cartridge read | That the file read is the file named | Whether that release is the one you meant |

A shape says nothing about what the part answers. That belongs to the members that model each part, such as [`snes-dsp-python`](https://github.com/gufranco/snes-dsp-python).

## Is it right

```bash
python3 -m conformance.against_cartridges
```

The sweep reads every cartridge it finds and prints each one's layout, its site count, its shape count and its four most frequent shapes. On the author's library it read 36 DSP cartridges, 0 of them silent. Three of them:

| Cartridge | Layout | Sites | Distinct shapes |
|:--|:--|--:|--:|
| Super Mario Kart (USA) | hirom | 122 | 18 |
| Pilotwings (USA) | lorom | 122 | 17 |
| Dungeon Master (USA) | lorom | 130 | 13 |

The other 6 cartridges in the manifest carry the `st`, `st018` and `obc1` parts. The sweep reads the DSP only, and none of the 6 was in the library it read. With no cartridge present the sweep exits 2. CI runs it on every push, treats exit 2 as a skip and annotates it.

[`conformance/hardware.json`](conformance/hardware.json) records every window with the evidence behind it, and [`conformance/hardware.test.py`](conformance/hardware.test.py) holds `WINDOWS` to it. No window is marked verified, because no manufacturer document gives the address lines a cartridge board decodes for a coprocessor. [`conformance/divergences.json`](conformance/divergences.json) records where a source is weaker than it looks, and [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists each unknown with the measurement that would settle it.

## Working on it

| Need | Where |
|:--|:--|
| Every gate and the order to run them, for a coding agent | [AGENTS.md](AGENTS.md) |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md) |
| Bug reports | [GitHub Issues](https://github.com/gufranco/snes-driver-python/issues) |
| Security reports | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
pnpm run format:check
python3 -m coverage erase
for file in $(find snesdriver conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
python3 -m conformance.speed
```

Each module has a test file beside it, named `<module>.test.py`, and each runs on its own. Coverage is a hard gate at 100% statement and branch, on a machine with the cartridge library and on one without. The throughput floor runs outside the coverage step. Commits follow [Conventional Commits](https://www.conventionalcommits.org/).

## References

- No manufacturer document is used. Nintendo's development manual, Book I, documents the memory map and the header and not the address lines a cartridge board decodes for a coprocessor. The DSP-1 application note in Book II would settle the windows.
- [`mos65xx-python`](https://github.com/gufranco/mos65xx-python), at the commit the submodule pins, for the 65816 instruction set.
- [`snes-mapper-python`](https://github.com/gufranco/snes-mapper-python), at the commit the submodule pins, for the cartridge layouts.
- A retail cartridge library the author owns, for the 36 cartridges read. Nothing from it is committed.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
