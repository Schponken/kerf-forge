# Step 1: Weigh it, then read it

Opinions about a repository are cheap and usually wrong in a predictable
direction: toward whatever the README said. Measure first.

## Fetch

```bash
bash scripts/fetch.sh owner/repo /tmp/teardown/repo      # tarball, no git needed
python3 scripts/weigh.py /tmp/teardown/repo
python3 scripts/weigh.py /tmp/teardown/repo --json       # for the post step
```

`fetch.sh` downloads and unpacks. It does not run anything from the repo, and
neither do you.

## What the numbers mean

| Output | Read it as |
|---|---|
| `weight class` | the blunt answer to "could I rebuild this" |
| `prose:code` | above 2:1, the product is the writing; below 0.3:1, the product is the code |
| `delegates to` | what the repo is standing on. Its real weight includes this |
| `carries the weight` | where to start reading. The top file is the repo |
| `markers` | which agent ecosystems it targets |
| `tests` | a repo with no tests and a confident README is a repo with no tests |
| `generated` | code nobody wrote. Subtract it before you judge the engineering |
| `notebooks` | counted in files, not lines: a .ipynb is code, prose and base64 output in one JSON |

**Weight classes:**

- **prompt-class**: under ~400 lines of code, or prose outweighing code 2:1.
  The artifact is the instructions. Rebuildable in a session.
- **small tool**: under 3000 lines. Readable end to end. Fork only if you want
  to maintain it.
- **medium tool**: under 20000 lines. Adopt or integrate. Rebuilding is a project.
- **fork-class**: a platform. Forking means owning a living codebase and its
  dependency updates forever.

A repo can be prompt-class and still be heavy: 200 lines of prompt over a video
renderer, a browser driver, or a model API is a thin steering layer on a thick
engine. Say both.

## Reading order

Not the README first. In this order:

1. **The heaviest file** from `carries the weight`. This is where the actual
   thinking lives.
2. **The entry point**: `bin/`, `main`, `index`, `cli`, or the `SKILL.md`.
3. **Whatever it delegates to.** If it npx's something, that something does the
   work, and you need to know whether *it* is the interesting part.
4. **Tests**, if any. Tests say what the author believed the contract was.
5. **The README, last.** By now you can tell which parts of it are true.

`--deep` reads every source file. Use it when the repo is prompt-class or small
tool, where "every file" is a real option.

## The ten questions

Answer all ten in writing before the verdict. Short answers. No hedging that
hides a gap. "Could not determine" is an answer, "appears to handle" is not.

```
1.  What does it do?
    One sentence, written by someone who read the code.

2.  What is the core mechanic?
    The one idea that makes it work. If you deleted it, what breaks?

3.  What does it ship vs what does it call?
    Its own code on one side, npx/pip/docker/model-APIs on the other.

4.  Where is the weight?
    Which file, and is the value in code, in prose, or in vendored assets
    someone else made?

5.  Claims vs code.
    Take the three loudest README claims. For each, find the file:line that
    implements it. Which one has nothing behind it?

6.  Does the weight class match how it presents itself?
    A "simple skill" with 30k lines, or a "framework" that is one prompt.

7.  Rebuild or adopt?
    Roughly what would reproducing the mechanic take, against installing it.

8.  What does it duplicate?
    In your stack, named as files or tools. Not "we have something similar".

9.  What is worth stealing regardless of the verdict?
    There is almost always one thing: a rubric, a threshold, a check, a phrasing.

10. What does adoption cost?
    Install footprint, files it writes, network calls, secrets it wants,
    what it does on first run, whether it touches your agent config.
```

## Assets are not authorship

A repo that bundles fonts, music, sound effects, or model weights is often
redistributing someone else's work. Check the license of the *assets*, not only
the repo. If the repo itself says the asset licensing is unverified, that is a
finding, and it means you source those assets yourself rather than copying
their bundle.
