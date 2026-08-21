# The family standard

These sixteen repositories are one family and are held to one standard. Where
they differ, the difference must be something the hardware forces, not something
nobody got round to.

| Repository | What it models |
|:--|:--|
| [mos65xx-python](https://github.com/gufranco/mos65xx-python) | The 65xx family, eight parts |
| [nec-upd7725-python](https://github.com/gufranco/nec-upd7725-python) | The DSP the SNES coprocessors are built on |
| [snes-driver-python](https://github.com/gufranco/snes-driver-python) | Reading a cartridge's own coprocessor protocol |
| [snes-dsp-python](https://github.com/gufranco/snes-dsp-python) | The DSP-1 to DSP-4 family |
| [snes-graphics-python](https://github.com/gufranco/snes-graphics-python) | The Super Nintendo graphics formats |
| [snes-mapper-python](https://github.com/gufranco/snes-mapper-python) | Cartridge headers and address decoding |
| [snes-obc1-python](https://github.com/gufranco/snes-obc1-python) | The OBC1 sprite remapper |
| [snes-rom-image-python](https://github.com/gufranco/snes-rom-image-python) | A cartridge image as a file |
| [snes-rtc-python](https://github.com/gufranco/snes-rtc-python) | The two cartridge real-time clocks |
| [snes-sdd1-python](https://github.com/gufranco/snes-sdd1-python) | The S-DD1 decompressor |
| [snes-spc7110-python](https://github.com/gufranco/snes-spc7110-python) | All three modes of the SPC7110 decompressor |
| [snes-st010-python](https://github.com/gufranco/snes-st010-python) | The two Seta coprocessors |
| [sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python) | The Sony S-DSP, on the clock schedule the hardware runs on |
| [sony-spc700-python](https://github.com/gufranco/sony-spc700-python) | The Sony SPC700, the audio unit's processor |
| [star-ocean-nochip-fix](https://github.com/gufranco/star-ocean-nochip-fix) | One header correction, end to end |
| [zilog-z80-python](https://github.com/gufranco/zilog-z80-python) | The Z80 |

## The authority ladder

Every factual question is answered by the highest rung that has an answer, and a
lower rung never overrules a higher one.

1. **Manufacturer documentation.** Anything printed decides. Read it in full
   rather than searching it, because the passages that matter are the ones
   nobody quotes.
2. **The part's own program or the artefact itself.** A cartridge, a firmware
   image, a header. What the silicon was actually asked to do.
3. **A recording from an independent implementation**, for behaviour nobody
   documented.
4. **Nothing else.** An emulator, an FPGA core, a wiki and a forum post are rung
   3 at best and rung 4 for anything printed.

A document that contradicts itself is common. When it does, the cycle table and
the pin descriptions have both times been right and the prose wrong.

**Never calibrate against an emulator where a document exists.** A recording is
evidence about behaviour nobody wrote down. It is not evidence about a register
width, a bit name, or anything else a manufacturer printed, however many
implementations agree with it. Where a recording contradicts a document, the
document wins, the disagreement is written down, and the model follows the
document.

**A recording whose answer depends on the machine it was built on is not evidence
at all.** It is a property of the recorder, and it is excluded and named rather
than allowed to decide.

## What every repository carries

| Gate | Standard |
|:--|:--|
| Format | `ruff format --check .`, clean |
| Lint | `ruff check .`, zero findings |
| Types | `mypy` at strict plus every optional error class, zero findings |
| Tests | `<module>.test.py` beside the module, run individually |
| Coverage | 100% statement and branch, enforced, on a machine holding no artefacts |
| JSON | `pnpm run format:check`, with every submodule tree exempted |
| CI | lint, types, tests on 3.12/3.13/3.14, plus the project's own conformance job |
| Schedule | a weekly run against unpinned tools and the newest runtime, starting on ground the pipeline never reaches |
| Analysis | CodeQL and Scorecard |
| Release | semantic-release from `main`, never tagged by hand |
| Docs | README, AGENTS.md plus the one-line pointer each tool reads, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT |
| Review | CODEOWNERS on every path, and templates that ask a report for the run that settles it |
| Specs | `specs/current/`, requirements with checkable scenarios |
| Hardware facts | `conformance/hardware.json`, every fact with the sentence it came from |
| Disagreements | `conformance/divergences.json`, both readings and what would settle it |

## Conventions that are not negotiable

| Thing | Rule |
|:--|:--|
| Language | Python only |
| Comments | None in source, ever. Docstrings carry the reasoning |
| Test structure | Arrange, blank line, one act, blank line, assert. No section labels |
| Nothing starts clean | Memory and registers hold what they held, from a seed |
| Artefacts | Never committed: no ROM, no firmware, no fragment of one |
| Only retail dumps | A ROM hack is somebody's edit, not what hardware ran |
| Package manager | pnpm, never npm |

## What a conformance runner must report

A runner asked about ground it has never been held to has three options and two
of them are lies. Reporting agreement lies about the part. Skipping in silence
lies about the run, because the summary then counts a comparison that never
happened. The third is to refuse: name what was compared, name what was not and
why, and count the two apart.

Report per part, never one number over parts with different evidence. One part
held to its manufacturer's manual and another held to nothing are not one figure.

## The state of this repository
## The state of this repository

**Nothing here rests on a document, because there is not one.** Nintendo's Book I
documents the memory map and the header, and says nothing about the address lines
a cartridge board decodes for a coprocessor. Searched on 2026-08-21. The DSP-1
application note in Book II would settle it and is not on this machine.

**What it rests on instead is the second rung, and a wide one.** The routine
inside a cartridge that drives its coprocessor is the only place the protocol is
written down, and this package reads that routine out of 36 cartridges. One
driver could be wrong about a window; thirty six independently written ones could
not be wrong the same way.

**An emulator agreeing is worth nothing here**, and
[`conformance/divergences.json`](conformance/divergences.json) says so outright.
Those emulators were written by people reading the same cartridge code this
package reads, so counting their agreement as corroboration would be counting one
piece of evidence twice.

**Every window carries `verified: false`**, and a test refuses to let one become
true without a document to promote it with. What the drivers still cannot say is
where a window stops: a driver shows where a part answers and never where it does
not.

**No cartridge is in this repository.** Only a manifest of names, lengths and four
digests each, and a digest reconstructs nothing. A file that is not the one named
is refused before a byte of it is disassembled, because disassembling the wrong
file would report a protocol nobody's hardware has, which is worse than reporting
nothing.

**Nothing here is a timing claim.** What one of these accesses costs the console
belongs to snes-mapper-python, and how long the part then runs belongs to
snes-dsp-python.
