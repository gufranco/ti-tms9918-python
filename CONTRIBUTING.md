# Contributing

## The short version

Evidence over assertion. A change that claims something is correct carries the
run that shows it, and a claim that cannot be checked is not ready.

## Before you open a pull request

Clone with the submodule, because the census drives the `zilog-z80-python`
processor:

```bash
git clone --recurse-submodules https://github.com/gufranco/ti-tms9918-python.git
```

The package itself imports nothing outside the standard library and installs on
its own. Only the census and its tests need the submodule. A source archive from
the download-zip link carries no submodule, so in that checkout the census tests
skip and say why.

Run every gate. The exit code decides; the output says what was found:

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

Run them at the versions the pipeline pins rather than whatever `python3` resolves to. A machine whose default interpreter moved on reports every suite as failing for want of a tool, which reads as broken code. The search is limited to the two source directories, so neither a stale `build/` copy of the package nor the submodule's own tests are collected.

Coverage is a hard gate at 100% statement and branch. A branch with no test fails
the build rather than lowering the number. `mypy` is strict and its findings are
errors.

## If you touch timing, the windows or a display mode

Three more things run, and none is optional.

`conformance/hardware.test.py` and `conformance/display.test.py` hold this
package's behaviour to the record, each test through the fact it names. A
citation in the documentation is therefore a check that can fail rather than a
claim in prose. It needs nothing outside the repository and runs in CI.

`python3 -m conformance.quotes` matches every quoted sentence against the TI
manual, once `python3 -m conformance.documents` has brought the manual down and
checked its digest.

The census needs an SG-1000 library you own, so it runs on your machine and not
on a runner:

```bash
python3 -m conformance.census "/path/to/your/library"
```

Paste the lines it prints. A property that breaks is a regression even when every
test passes: a retail image that never turns the display on is software that worked
on the chip and does not work here. A change in the count of lost accesses is not a
failure on its own, but it says the windows moved, so explain it.

## Tests

A test file sits beside the module it covers and is named after it. Each test is
three blocks, opened by bare `# Arrange`, `# Act` and `# Assert` markers and
separated by one blank line each. Those markers are the only comments a test
carries, and the test name says what behaviour is being pinned. Expected values
come from the manual or from a worked example, never from running the code.

## Commits

Conventional Commits, subject under fifty characters, imperative mood. The body
explains what changed and why, wrapped at seventy two columns. Releases are cut
by semantic-release from those subjects, so the type is what decides the version.

## What will be sent back

- A file nobody can legally redistribute, or a digest of one fine enough to
  reconstruct it. Whole-file digests are welcome; per-block ones are not.
- A number in a document that no run produced.
- A behaviour changed without the corpus or the record moving with it.
- A test that asserts what the code does rather than what the hardware does.

## What is welcome without asking

Measurements. A logic analyser capture of RAS, CAS and R/W on a running
TMS9918A, TMS9928A or TMS9929A would settle most of `OPEN-QUESTIONS.md` at once.
