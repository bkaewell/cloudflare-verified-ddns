# Contributing to cloudflare-verified-ddns

Thanks for considering contributing! This project aims to provide a reliable, secure, and minimal DDNS client that verifies changes against Cloudflare's API - keeping your domains pointed correctly with zero fluff.

We welcome contributions of all kinds: code, docs, bug reports, testing on diverse networks, CI ideas, or even packaging help. All input helps make this tool more robust for real-world use.

Before starting, please read our [Code of Conduct](CODE_OF_CONDUCT.md) (Contributor Covenant v3.0). By participating, you agree to follow it.

## Quick Start for Contributors

1. **Found a bug or have an idea?**
   - Check existing [issues](https://github.com/bkaewell/cloudflare-verified-ddns/issues) first.
   - If none match, open one using the templates (bug report / feature request).
   - For security issues (e.g., token handling), email privately: **<conduct@briankaewell.com>**.

2. **Ready to code?** Fork & clone:

   ```bash
   git clone https://github.com/bkaewell/cloudflare-verified-ddns.git
   cd cloudflare-verified-ddns
   ```

3. **Development Setup**
   
   ```bash
    uv sync --dev       # Install deps + dev tools (Ruff, pytest, etc.)
   ```

   Run locally:
   ```bash
   uv run --env-file .env -m app.main       # Loads environment variables from your .env file
   ```

   (Tip: Use a test Cloudflare zone/API token—never commit real creds!)


4. **Testing**
   
   ```bash
   uv run pytest -v
   ```
 
   With coverage:
   ```bash
   uv run pytest --cov=app --cov-report=term-missing --cov-report=html
   ```

   Open `htmlcov/index.html` to view

5. **Linting & Formatting** (enforced via pre-commit)

   ```bash
   uv run pre-commit run --all-files
   ```

   (We use Ruff + Black + mypy—commit hooks auto-run on install.)

## Branching & Commit Guidelines

  - Branch from `main`.
  - Use descriptive names: `fix/doh-timeout`, `feat/prometheus-metrics`, `docs/add-ipv6-guide`, `chore/update-deps`.
  - Commit messages: Conventional style (e.g., `feat: add IPv6 support`, `fix: handle 429 rate limits`, `docs: clarify token scopes`).
    - Keep subject <72 chars, body explains why + how if non-obvious.
  - Sign commits if possible (`-S` flag) for verification.

## Pull Requests

Thanks for wanting to contribute!

To make reviews fast and high-quality, we use a structured pull request template. Please fill out **all required sections** when opening a PR.

### How to open a good PR

1. Make sure you've read and followed the steps in the pull request template
2. Run tests locally: `uv run pytest`
3. Update documentation if the public interface / config / behavior changed
4. Link related issues with `Closes #123` or `Related to #456`
5. Rebase on latest `main` and squash fixup commits before opening

When you open a PR against this repository, GitHub will automatically pre-fill the description with our [pull request template](PULL_REQUEST_TEMPLATE/pull_request_template.md).

A GitHub Actions workflow called **PR Lint** will automatically check that:
- The PR has a clear one-sentence **Summary**
- A **Type of change** is selected
- **Motivation / Related issue** explains the why (not just "see summary")
- The **Checklist** at the bottom has most/all relevant boxes checked

If something is missing, the check will fail (red X) and a comment may appear asking for fixes.

### We highly recommend

- Use Conventional Commits style for the PR title (optional but appreciated):  
  `feat: add multiple zone support`  
  `fix: handle token expiry during refresh`  
  `docs: improve configuration examples`  
  `chore(deps): bump cloudflare python sdk`

Thank you — high-quality PRs get merged much faster! 🚀

## Recommended Labels

Use these when filing/triaging:
  - `good first issue` — beginner-friendly, well-scoped.
  - `help wanted` — needs extra eyes or skills.
  - `enhancement` — new feature or improvement.
  - `bug` — something broken.
  - `security` — potential vuln (handle privately!).
  - `docs` — documentation only.

## Non-code Contributions

  - Improve docs (typos, clearer examples, Cloudflare gotchas).
  - Test on edge cases (CGNAT, IPv6-only, flaky networks).
  - Suggest CI/CD enhancements (GitHub Actions matrix, etc.).
  - Triage issues, answer questions in Discussions.

## Community & Questions

  - Use [GitHub Discussions](https://github.com/bkaewell/cloudflare-verified-ddns/discussions)for ideas, questions, design chats.
  - Chat in issues/PRs for code-specific topics.

Thanks again—your contributions make this project better for everyone running dynamic home labs, edge nodes, or self-hosted services.

Happy hacking!
