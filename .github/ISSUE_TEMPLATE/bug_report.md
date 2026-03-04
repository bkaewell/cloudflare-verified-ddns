name: 🐛 Bug Report
description: Report a reproducible problem
title: "[BUG] "
labels: ["bug", "triage-needed"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for reporting! Please fill out the sections below — incomplete reports may be closed.

  - type: input
    id: summary
    attributes:
      label: Summary
      description: One-sentence description of the bug
      placeholder: "DDNS update fails with 403 when using scoped token"
    validations:
      required: true

  - type: dropdown
    id: deployment
    attributes:
      label: Deployment mode
      options:
        - Docker Compose
        - Single Docker container
        - Local (python -m ...)
        - Other (please specify below)
      default: 0
    validations:
      required: true

  - type: input
    id: version
    attributes:
      label: Version / Commit
      description: Container tag, git commit hash, or PyPI version
      placeholder: "v1.2.3 / ghcr.io/username/cloudflare-verified-ddns:latest"
    validations:
      required: true

  - type: input
    id: os
    attributes:
      label: Operating system / Host OS
      placeholder: "Ubuntu 24.04 / Debian 12 / macOS 15 / Windows Server 2022"
    validations:
      required: true

  - type: textarea
    id: steps
    attributes:
      label: Steps to Reproduce
      description: Numbered list — be specific!
      placeholder: |
        1. docker compose up -d
        2. Change public IP
        3. Wait 5 minutes
        4. See error in logs
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected behavior
      placeholder: "A record should update silently to new IP"
    validations:
      required: true

  - type: textarea
    id: actual
    attributes:
      label: Actual behavior
      placeholder: "HTTP 403 Forbidden — token lacks zone:edit permission"
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: Logs / Screenshots
      description: Paste relevant logs (redact API tokens, IPs, zone names). Use ``` for formatting.
      render: shell

  - type: textarea
    id: extra
    attributes:
      label: Additional context
      description: Anything else? (related config.yaml snippet, Cloudflare zone settings, etc.)

  - type: checkboxes
    id: checklist
    attributes:
      label: Checklist
      options:
        - label: I searched existing issues and this is not a duplicate
          required: true
        - label: I am using the latest release / git main
          required: true
