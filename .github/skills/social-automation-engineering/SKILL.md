---
name: social-automation-engineering
description: Build maintainable social automation pipelines with validation, observability, retries, secrets hygiene, and verifiable artifacts.
---

# Social Automation Engineering

## Engineering standards
1. Inspect repository conventions before changing files. Make scoped changes and inspect existing content before overwriting user files.
2. Define inputs, outputs, dependencies, environment variables, artifacts, failure modes, and acceptance tests before implementation.
3. Validate configuration and input files before network calls or expensive generation.
4. Store credentials in environment secrets; redact tokens, cookies, authorization headers, and personal data from logs.
5. Use timeouts, bounded retries, exponential backoff, rate-limit handling, and idempotent job IDs.
6. Emit structured logs with job ID, stage, duration, status, and sanitized error.
7. Add unit tests and an integration smoke test that runs without live publishing.
8. For CI workflows, use least-privilege permissions, explicit concurrency, dependency pinning, dry-run defaults, and clear artifact paths.
9. Never infer success from process exit alone. Verify output files and expected metadata.
10. For videos, verify files exist, are non-empty, and contain decodable audio/video streams; count outputs and record exact paths.
11. Produce a run summary: commit SHA, workflow run ID, inputs, outputs, test results, skipped work, and unresolved issues.
12. Prefer free/open-source components where practical, but disclose hardware, model-license, quota, and GPU constraints. Verify current terms before calling a service free.
