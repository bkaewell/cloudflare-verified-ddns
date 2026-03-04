<!--
Thanks for contributing to cloudflare-verified-ddns! 🚀

High-quality PRs get merged fastest. Please fill out **all required sections** below.
Incomplete PRs may be labeled "needs-info" or closed after a polite nudge.

Before submitting:
- Ran tests locally? (`uv run pytest`)
- Updated docs if needed?
- No secrets / credentials added?
- Linked related issue(s)?
-->

## Summary

**One-sentence description** of the change and its purpose.

Example: "Add support for multiple Cloudflare zones via config array to reduce container sprawl"

## Type of change

- [ ] Documentation update / typo fix
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change / major refactor
- [ ] Maintenance / dependency update
- [ ] CI / build / deployment improvement

## Impact / Risk level

- [ ] Low – isolated, easy to revert
- [ ] Medium – affects core DDNS logic or config
- [ ] High – touches Cloudflare API calls, auth, or container entrypoint

## Motivation / Related issue

- Closes # (replace with issue number(s), e.g. Closes #42)
- Related to # (if not closing but connected)

**Why is this change needed?**  
(Brief context: user pain point, performance gain, security fix, enterprise use-case, etc.)

## Proposed solution / Implementation notes

- High-level how: what was changed?
- Key files modified:
- Any new dependencies?
- Breaking changes or migration steps for users?

(Feel free to be technical — senior reviewers appreciate details like "Switched to `cf_api.v4.zones.records.put()` for atomic updates".)

## Testing done

- [ ] Unit / integration tests added / passed (`uv run pytest`)
- [ ] Manually tested in Docker Compose
- [ ] Manually tested in single-container mode
- [ ] Manually tested in local CLI mode (`python -m cloudflare_verified_ddns ...`)
- [ ] Edge cases covered (e.g. token expiry, rate limits, IPv6, multiple zones)

**Test environment details** (optional but helpful):  
OS / Docker version / Cloudflare setup (proxied? DNS-only?):

## Screenshots / Logs (if UI or output visible)

(Drag & drop images here or paste command output / container logs)

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I have rebased my branch on the latest main
- [ ] I have squashed fixup commits
- [ ] No secrets / .env / credentials were committed (double-checked with `git diff`)

Thank you for your contribution!  
Reviewers will get back to you as soon as possible.
