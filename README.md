# SNES Driver

What a cartridge says to its coprocessor, read out of the cartridge's own code.

[![CI](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml)

**36** cartridges read, **0** disagreements with their own digests, **2** layouts, **3** kinds of access, **464** tests, **100%** statement and branch coverage, no dependencies

```python
from snesdriver import at, window_for

routine = bytes(
    [
        0xE2,
        0x20,
        0xA9,
        0x01,
        0x8F,
        0x00,
        0x60,
        0x00,
        0xC2,
        0x20,
        0xAF,
        0x00,
        0x70,
        0x00,
        0xAF,
        0x00,
        0x60,
        0x00,
        0x60,
    ]
)

print(at(routine + bytes(2048), 0, window_for("dsp", "hirom")).shape)
```

```
write1 poll2 read2
```

One byte of command, a poll of the status register, then a two byte answer. That
sequence is what a model has to be told, and the cartridge's own code is the only
place it is written down.


## Install

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-driver-python.git
cd snes-driver-python
```

Python 3.12 or newer. Nothing else at runtime.

> [!IMPORTANT]
> The download-zip link on the repository page produces a checkout that cannot
> run. A source archive cannot carry a submodule, and both the disassembler and
> the memory map are submodules. Clone with `--recurse-submodules`, or run
> `git submodule update --init` in a checkout that already exists.

This package is not installable from an index and carries no `[project]` block,
because it consumes two other members as submodules rather than as version
ranges.

## The interface

Nothing here is executed. Every call is a question about a cartridge's own code.

| Call | Does | Returns |
|:--|:--|:--|
| `window_for(part, layout)` | Where that part answers under that layout, or nothing when it does not | a `Window` or `None` |
| `sites(rom, window)` | Every instruction in the image that reaches the part | offsets |
| `at(rom, offset, window)` | The whole exchange one routine performs | a `Conversation` |
| `shapes(rom, window)` | Every distinct exchange in the image, with how often each occurs | a mapping |
| `through(rom, offset)` | The routine walked instruction by instruction | `Step` objects |
| `busiest(shapes)` | The exchange that occurs most | a shape |

| Attribute | Is |
|:--|:--|
| `conversation.shape` | The exchange as a string, each access named and sized |
| `conversation.steps` | Each access: what it was, where it landed, how wide |
| `conversation.covered` | The sites this exchange already accounted for |
| `window.data` / `window.status` | The two addresses the part answers at |
| `window.first_bank` / `window.last_bank` / `window.end` | Which banks, and how far into each |
| `WINDOWS` | Every part, and the layouts each is known under |

`UnknownPart` is raised for a name no part goes by, rather than answered with
nothing, because nothing is already the answer to a different question: a part
that exists and does not answer under the layout asked about.

There is no clock and no model. What a coprocessor answers belongs to the members
that model those parts.

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

## How it reads

Nothing is executed. A routine is walked straight through, from its first instruction to the first one that leaves, and every instruction is asked what it reached.

```python
from snesdriver import through

routine = bytes([0xE2, 0x20, 0xA9, 0x01, 0x8F, 0x00, 0x60, 0x00, 0x60])

for step in through(routine + bytes(2048), 0):
    print(step.mnemonic, step.width)
```

```
sep 1
lda 1
sta 1
rts 1
```

The part that cannot be skipped is width. A store to a coprocessor moves one byte or two depending on the accumulator, and the accumulator's width is not in the instruction: a `sep` or a `rep` set it earlier. A walk that ignores those reads every access at the wrong size and reports an exchange the console never had.

The store above is one byte wide because the `sep` two instructions earlier made
it so. Take the `sep` away and the same three bytes move two.

Which register an access lands on is decided by the layout, not by the part. The same DSP answers at `$30-3F:8000` in a low cartridge and `$00-0F:6000` in a high one, and the line that picks between data and status is address bit 14 in the first case and bit 12 in the second.

```python
from snesdriver import WINDOWS, window_for

print({part: sorted(layouts) for part, layouts in sorted(WINDOWS.items())})

low = window_for("dsp", "lorom")
high = window_for("dsp", "hirom")

print(f"{low.data:#06x} {low.status:#06x}")
print(f"{high.data:#06x} {high.status:#06x}")
```

```
{'dsp': ['hirom', 'lorom'], 'obc1': ['lorom'], 'st': ['lorom', 'lorom-shared'], 'st018': ['lorom']}
0x8000 0xc000
0x6000 0x7000
```

Every site in an image and every distinct exchange it performs come out of the
same walk:

```python
from snesdriver import shapes, sites, window_for

routine = bytes(
    [
        0xE2,
        0x20,
        0xA9,
        0x01,
        0x8F,
        0x00,
        0x60,
        0x00,
        0xC2,
        0x20,
        0xAF,
        0x00,
        0x70,
        0x00,
        0xAF,
        0x00,
        0x60,
        0x00,
        0x60,
    ]
)
image = routine + bytes(2048)
window = window_for("dsp", "hirom")

print([f"{one:#06x}" for one in sites(image, window)])
print(shapes(image, window))
```

```
['0x0004', '0x000a', '0x000e']
{'write1 poll2 read2': 1}
```

Three sites and one shape, because a routine that writes and then reads is one
exchange rather than three.

## Bringing your own cartridges

Every cartridge is confirmed against four digests before a byte of it is disassembled. `sha256` decides; the other three are confirmed too, because a file can be the right length under the right name and still be a bad dump.

That check is not ceremony here. A file that is not the one named would be disassembled anyway and would report a protocol nobody's hardware has, which is worse than reporting nothing. Every filename and all four digests are printed in [`cartridges/README.md`](cartridges/README.md) so a copy can be checked before it is supplied.

Nothing in that directory is shared, and no part of any cartridge is reconstructible from anything here.

## What each piece of evidence is worth

| Evidence | What it settles | What it cannot |
|:--|:--|:--|
| The cartridge's own code, walked instruction by instruction | What a shipped game actually sends to the part | Anything no game sends |
| The 65816 instruction set, through the disassembler | What each instruction is and how wide its access | Nothing about the part on the other end |
| The layout the header declares, through the mapper | Which addresses reach the part | Nothing about what happens when they do |
| Digests of every cartridge read | That the file read was the file named | Nothing about whether that release is the one you meant |

A shape is evidence because it is the cartridge's own sequence in the order the
console runs it. It is not evidence about what the part answers, which is the
sibling project's job, and it says nothing about games nobody dumped.

## Is it right

Read across the 36 DSP cartridges on hand, each confirmed against all four of its
digests before a byte of it is disassembled.

| Cartridge | Layout | Sites | Distinct shapes |
|:----------|:-------|------:|----------------:|
| Super Mario Kart | hirom | 122 | 13 |
| Pilotwings | lorom | 122 | 17 |
| Dungeon Master | lorom | 130 | 13 |

A **site** is one instruction that reaches the part. A **shape** is one routine's
whole exchange. Those differ because a routine that writes and then reads is one
exchange rather than two, so a site an earlier walk already stepped over does not
start a conversation of its own. Reporting the tail of a routine as though it
were the whole thing is the mistake that makes this look easier than it is.

```bash
python3 -m conformance.against_cartridges
```

That sweep is skipped rather than passed when no cartridge is present, so a run
that proved nothing never reads as a run that proved something. CI attempts it on
every push and annotates the skip.

[`conformance/hardware.json`](conformance/hardware.json) holds what this package
asserts about each window and where each assertion comes from.
[`conformance/divergences.json`](conformance/divergences.json) holds where a
source is weaker than it looks, and [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md)
carries every place fidelity here is a claim rather than a measurement. The
largest of those is that no manufacturer document gives any of these windows.

## Working on it

```bash
python3 -m coverage erase
for file in $(find snesdriver conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

| Suite | File | Covers |
|:------|:-----|:-------|
| Windows | [`snesdriver/windows.test.py`](snesdriver/windows.test.py) | Where each part answers under each layout |
| Walk | [`snesdriver/walk.test.py`](snesdriver/walk.test.py) | Accumulator width, where a routine ends, what each instruction reached |
| Conversation | [`snesdriver/conversation.test.py`](snesdriver/conversation.test.py) | Writes, reads, polls, shapes, and counting a routine once |
| Cartridges | [`conformance/cartridges.test.py`](conformance/cartridges.test.py) | The manifest and all four digests |
| Sweep | [`conformance/against_cartridges.test.py`](conformance/against_cartridges.test.py) | Every cartridge present, read |

The last one is skipped rather than passed when no cartridge is present, so a run that proved nothing never reads as a run that proved something. CI attempts it on every push and annotates the skip.

`python3 snesdriver/doctor.py` says what is actually on this machine: every window, a routine walked out of bytes assembled on the spot, and whether the submodules this repository needs are checked out. It is run as a file rather than with `-m` so that it still runs when the package itself will not import, which is the case it exists for. Its report is what an issue asks for, because a report is only as good as what it says about the machine that produced it.

Coverage is enforced at 100% of statements and branches, and it holds both on a
machine with the whole library and on one holding nothing. That second half is the
part worth stating: a suite whose number depends on what the machine happens to
contain is not measuring the code. The only thing outside the gate is the test
class whose subject is a real library, and it says so where it sits.

### Development

| Command | Description |
|:--|:--|
| `ruff format .` | Format |
| `ruff check .` | Lint |
| `mypy` | Types, at strict, with every optional error class on |
| `python3 -m coverage run -a <file>` | Run one test file under coverage |
| `python3 -m coverage report` | Coverage, which fails below 100% |
| `python3 -m conformance.against_cartridges` | Read every cartridge on this machine |
| `python3 -m conformance.speed` | The throughput floor |
| `pnpm run format:check` | Check that every JSON file is formatted |

### Project conventions

| Convention | Source |
|:--|:--|
| Commit format | [Conventional Commits](https://www.conventionalcommits.org/) |
| Formatting and lint | [ruff](https://docs.astral.sh/ruff/), configured in [`pyproject.toml`](pyproject.toml) |
| Types | [mypy](https://mypy.readthedocs.io/) at strict, configured in [`pyproject.toml`](pyproject.toml) |
| Versioning | [semantic-release](https://semantic-release.gitbook.io/), from the commit history |
| Tests | Beside the module, named `<module>.test.py` |


[`AGENTS.md`](AGENTS.md) is the document for an agent working here.
[`FAMILY.md`](FAMILY.md) is the standard this repository shares with the rest of
the family, kept identical in every member above the marker at the end of its
shared part.

## References

This repository carries no documents and no cartridges.

**No manufacturer document gives any of these windows.** Most of these parts have
no surviving datasheet, and the emulators that talk to them were written by people
who read the same cartridge code this package reads. That leaves the top rung of
the authority ladder empty, which is recorded in
[`conformance/hardware.json`](conformance/hardware.json) rather than papered over
by promoting the rung below it.

### What this is built on

Both sit at the repository root, each named after itself rather than buried under
a generic folder, so what this is built on is visible the moment the repository
is opened.

| Package | At | Does |
|:--|:--|:--|
| [`mos65xx-python`](https://github.com/gufranco/mos65xx-python) | `mos65xx-python/` | Disassembles the 65816, which is what a driver routine is written in |
| [`snes-mapper-python`](https://github.com/gufranco/snes-mapper-python) | `snes-mapper-python/` | Decides which layout a cartridge declares |

| Source | Used for |
|:-------|:---------|
| A retail cartridge library the author owns | The 36 cartridges read. Nothing from it is committed, and [`cartridges/README.md`](cartridges/README.md) carries only filenames and digests |

## Citing this

[CITATION.cff](CITATION.cff) is kept in step with the released version by the
same script that stamps the package, so the version it names is the version that
shipped.

## License

MIT. See [`LICENSE`](LICENSE).
