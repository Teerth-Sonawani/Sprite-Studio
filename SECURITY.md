# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.x | Yes |
| < 1.0 | No |

## Reporting a vulnerability

Please do not open a public issue for a security problem.

- Use GitHub's **Security → Report a vulnerability** flow (private security
  advisory) for this repository, or
- Contact the repository owner privately through the contact details on their
  GitHub profile.

Include the affected version or commit, a description of the issue, reproduction
steps, and the impact you believe it has. Redact any real API keys or account
data. You should receive an acknowledgement, and a fix or mitigation will be
coordinated before public disclosure.

## Security model

This project is a local, file-driven workspace. It does not run a server or
accept untrusted network requests. The relevant risks are therefore mostly about
credentials, generated files and provider calls.

### Credentials

- The only supported PerchanceAI credential source is the environment variable
  `PERCHANCEAI_API_KEY`.
- Credentials are never accepted as CLI flags, written to prompts, manifests,
  logs, QA reports or signed output URLs.
- `.env` is ignored by git; only `.env.example` with placeholders is tracked.
- Do not paste keys into issues, pull requests, screenshots or prompt files.

### Charged provider calls

- A chargeable request requires a prior estimate, a budget limit and `--confirm`.
- Idempotency records are written before submission.
- An uncertain submission must not be retried automatically with a new
  idempotency key. Check the provider status first.
- The project deliberately does not bypass Cloudflare, reverse-engineer private
  endpoints or automate browser challenges.

### Unsupported integrations

- The documented `perchance.org/api-tutorial` endpoint returned HTTP 404 during
  the build and is reported as unsupported.
- The developer API adapter is implemented from documentation. A live charged
  generation was not exercised in the original build, so treat provider paths as
  code-reviewed but not production-proven.

### Generated files and manifests

- Manifests store relative paths and SHA-256 hashes.
- File paths are resolved defensively during export, but treat manifests and
  briefs from untrusted sources as data, not as trusted code.
- The example exports are import aids, not a substitute for opening the project
  in the target engine.

## Dependency and supply-chain notes

- Runtime dependencies are declared in `pyproject.toml` and `requirements.txt`.
- Optional video previews use `imageio` and `imageio-ffmpeg`; the bundled FFmpeg
  build has its own licence and update cadence.
- Dependabot is configured for pip and GitHub Actions updates.
- No third-party code is vendored in this repository.
