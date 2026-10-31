# Step 2: The verdict

Write `teardown-<repo>.md`. One page. It has to be readable by someone who will
never open the repo.

## Shape

```markdown
# Teardown: owner/repo

**Verdict: ADOPT | STEAL | SKIP.** <One line of why>

## What it is
[One paragraph. The mechanic, in plain words. What the repo actually does when
you run it, not what category it belongs to.]

## Weight
- Class: [prompt-class / small tool / medium tool / fork-class]
- Code: [N] lines · Prose: [N] lines · Tests: [N] lines
- Standing on: [what it delegates to]
- Real weight: [its own weight + what it delegates to, in one line]

## Claims vs code
| README says | Code says | Where |
|---|---|---|
| "<claim>" | implemented | `path/file.py:120` |
| "<claim>" | claimed, not verified | nowhere |

## The mechanic worth naming
[The one idea. Two or three sentences. This is the part a reader remembers, and
the part you would reimplement if the verdict is STEAL.]

## What's in it for us
- Overlaps with: [our own files/tools, named]
- Cost to adopt: [install, writes, network, secrets]
- Worth taking regardless: [the one thing]
- Breaks if adopted: [what]

## Verdict
[Two or three sentences. What you are doing about it, and what you are not.]
```

## Choosing the verdict

**ADOPT** when the work inside exceeds the work of rebuilding it, the license
permits it, and the install footprint is something you would accept from a
stranger. Adopting an agent skill means putting someone else's instructions into
your model's context. Judge it as code you are running, because it is.

**STEAL** when the idea is good and the implementation is small. Most
prompt-class repos land here. Stealing means writing your own version, in your
own words, against your own stack, with credit to the source. It does not mean
copying files and changing the name.

**SKIP** when it duplicates something you have, when the mechanic is thinner
than the README, when the assets are the only value and their license is
unclear, or when adopting it would cost more attention than it returns.

There is no fourth verdict. "Interesting, let's keep an eye on it" is SKIP with
extra steps. If it matters later, run the teardown again when it does.

## Things that look like findings and are not

- **Star count, trending badges, fork count.** A repo can be promoted. Stars
  measure promotion reaching people, not the code working.
- **A long README with screenshots.** Cheap to produce.
- **A list of supported agents/platforms.** Usually a table of directory paths,
  not integration work.
- **"Used in production by …"** with no link.
- **Its own benchmark numbers** with no reproduction script.

## Things that are findings and get written down

- A confident claim with no implementation behind it.
- A repo whose entire value is vendored third-party assets.
- An install step that writes outside the project, or overwrites an agent's
  config directory.
- Network calls that are not mentioned in the README.
- A prompt that instructs the agent to skip verification, trust the repo, or
  treat its own text as authoritative.
- A license on the repo that does not cover the assets inside it.
