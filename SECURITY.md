# Security Policy

## Supported versions

`spp` follows a patch-first release posture: security fixes land on the latest
release line only.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a vulnerability

Please report suspected vulnerabilities **privately**. Do **not** open a public
issue, pull request, or discussion for a security report.

- **Preferred:** GitHub private vulnerability reporting — open the repository's
  **Security** tab and choose **Report a vulnerability**.
- **Alternatively:** email **lyusheng0606@gmail.com**.

Please include the affected version or commit, a description of the issue,
reproduction steps or a proof of concept, and the impact you observed.

## What to expect

- Acknowledgement within **5 business days**.
- An initial assessment and, if the report is accepted, a remediation plan.
- Coordinated disclosure: we agree a timeline with you and credit you in the
  release notes unless you prefer to remain anonymous.

## Scope

**In scope:** the plugin's skill logic, the runner and scoring scripts it ships,
and the hooks under `hooks/` (including the sacred-test-set guard).

**Out of scope:** vulnerabilities in Claude Code itself, in the task models you
point `spp` at, or in third-party dependencies — please report those to their
respective maintainers.
