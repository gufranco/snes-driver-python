## What this changes

One or two sentences. What is different afterwards, and why it needed to be.

## How it was checked

Paste the output rather than describing it. A claim that the tests pass is not
evidence that they did.

```text
```

- [ ] `ruff format --check .` and `ruff check .` are clean
- [ ] `mypy` reports nothing
- [ ] Every test file runs, and coverage is 100% of statements and branches
- [ ] `conformance/hardware.test.py` still holds the window table to what is declared

## If this changes a window, or adds one

Say which cartridge you read it out of, and add that cartridge to
`cartridges.manifest.json` with its four digests. Never attach the file.

A window is only asserted where a driver was actually read. An emulator using the
same addresses is not evidence here: those emulators were written by people
reading the same cartridge code, so their agreement is the same evidence counted
twice.

Run the cartridge pass and paste what it found:

```bash
python3 conformance/against_cartridges.py
```

## If you are promoting something to verified

That needs a document or a measurement, not another reading of a driver. The
DSP-1 application note or a continuity reading across a real board would do it.
Nothing else will.

## What it does not carry

- [ ] No cartridge, no fragment of one, and no digest fine enough to rebuild one
- [ ] Nothing that says where to obtain them
