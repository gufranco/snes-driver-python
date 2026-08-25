# Security

## Reporting

Report anything you believe is a security problem through
[GitHub's private vulnerability reporting](https://docs.github.com/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
on this repository, rather than in a public issue. There is no service behind
this and no user data, so the realistic reports are about the supply chain and
about what a malformed input can make the code do.

## What is in scope

| Class | Example |
|-------|---------|
| Supply chain | A dependency, a submodule or a pinned action that has been compromised |
| Malformed input | A crafted image that makes the walker allocate without bound, follow a branch without end, or read outside the window it was given |
| Path handling | An input that causes a read outside the directory the caller named |
| Disassembly | A byte sequence that drives the decoder past the end of what it was handed |

## What is not

A window this package reports at the wrong address is a correctness bug and
belongs in a normal issue. So is a conversation it reads differently from the
cartridge. Neither is a security matter, and filing them privately only slows
the fix.

## What this repository will not do

It does not fetch anything at runtime, and nothing here downloads a cartridge or
a firmware image. Any file it reads is one already on the machine because
somebody put it there. That is a deliberate limit rather than an omission: a tool
that fetches on your behalf is a tool that decides for you what you are allowed
to be given.
