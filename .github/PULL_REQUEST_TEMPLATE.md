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
- [ ] Every new check was run once against input that should fail it

## If this changes timing, the windows or a display mode

The tests alone do not check a change here. Run the census over an SG-1000 library
you own and paste what it prints:

```text
  ok    the model raises on no image: 0 broken
  ok    every retail image turns the display on within the frame bound: 0 broken
  observed  accesses asked for before the last one was served: N images
```

Deduplicate by digest before quoting a count. A library organised by series
lists the same image several times.

## What it does not carry

- [ ] No cartridge, no fragment of one, and no digest fine enough to rebuild one
- [ ] Nothing that says where to obtain them
