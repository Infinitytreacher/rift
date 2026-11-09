<!-- SPDX-FileCopyrightText: 2026 Siddhant Tiwari -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

# Security and privacy

RIFT is a course prototype for trusted local demonstrations.
It does not provide the access controls required for a public service.
No formal support policy or security response deadline is established.

## Data handling

Do not use real student data for an unprotected demonstration.
Obtain consent and the required institutional permission before recording or processing lectures.
Use synthetic recordings or material that you are authorized to process.

SQLite stores complete transcripts, extracted topics, ratings, and timestamps.
The session API returns complete transcripts without authentication.
The survey does not collect names or require accounts, but the application does not guarantee anonymity.
Server logs, network records, recordings, and timestamps can identify people.

The request handler deletes its temporary audio file after processing.
Process termination can bypass cleanup. Inspect the configured upload directory after a failed run.
No automatic retention policy deletes transcripts or feedback.
Backups and copied databases need the same protection as the live database.

Whisper weights come from Hugging Face unless cached.
Transcription runs in the local Python process.
Ollama receives the transcript at `OLLAMA_BASE_URL`. A remote URL sends lecture content to that server.
The dashboard also loads JavaScript from a public CDN.

## Deployment constraints

Do not bind this application to a public interface without a separate security review.
The launcher defaults to `127.0.0.1` and does not load the original TLS files automatically.
CORS permits no cross-origin browser access by default, but it does not restrict direct API clients.

Before access outside the local machine, address these gaps:

- Authentication and authorization for uploads, dashboards, status, and transcripts.
- Request limits, rate limits, audio validation, and resource isolation for inference.
- A defined retention policy and restricted access to databases, logs, and backups.
- Database constraints and prevention of duplicate or forged feedback.
- Trusted HTTPS, pinned browser dependencies, and appropriate browser security headers.
- Dependency auditing and end-to-end tests using approved models and consented inputs.

Application logs can still include exception messages from libraries.
Treat local logs as private even though routine topic text, filenames, and course names are no longer logged.
Do not put credentials in the Ollama URL or paste raw logs into a public issue.

## Git and exposed credentials

The original repository tracks a private TLS key and sensitive runtime artifacts.
Both existing commits contain the key and database.
Treat the key as compromised, even if no remote is currently configured.
Replace it and its certificate. If a certificate authority issued the certificate, follow its revocation process.
Rotate any credential that reused the key or was otherwise exposed.

`.gitignore` only prevents new untracked files from being added by ordinary Git commands.
It does not protect tracked files, old commits, forks, backups, or existing releases.
See [PUBLICATION_REVIEW.md](PUBLICATION_REVIEW.md) for actions that require maintainer approval.

Do not publish the current history as a source archive.
The `/source` endpoint uses an explicit public-file list and rejects missing files and linked paths.
Keep that list complete when modifying the application.

## Reporting a concern

Do not include private data or exploitable credentials in a public issue.
If no private reporting channel is available, ask the maintainer to establish one before sharing sensitive details.
No repository URL or private contact address is assumed here.
