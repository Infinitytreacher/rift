<!-- SPDX-FileCopyrightText: 2026 Siddhant Tiwari -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

# Publication review

Status: blocked for public release.
The source cleanup does not make the existing repository history safe to publish.
This review covers the local checkout and its two reachable commits, not unknown remotes, backups, or prior distributions.

## Findings and actions

| Finding | Verified evidence | Action |
| --- | --- | --- |
| Tracked private TLS key | `key.pem` occurs in both reachable commits | Replace the key and certificate, address revocation where applicable, and approve Git cleanup |
| Tracked local certificate | `cert.pem` occurs in both commits | Exclude it from the release and review any embedded local identifiers |
| Tracked lecture and rating database | `feedback_system.db` contains 9 sessions, 59 topics, and 94 feedback rows | Preserve privately, then approve removal from the index and release history |
| Tracked compiled Python | Four files under `__pycache__/` occur in both commits | Exclude compiled files and remove historical copies with approval |
| Tracked legacy archive | `E.zip` contains nine older source/documentation files | Exclude this stale copy and remove historical copies with approval |
| Private contact details | The original `COPYRIGHT.md` contains contact addresses in both commits | Current notice is sanitized, but old copies remain in history |
| Hard-coded local network address | Original `main.py` and `static/record.html` contain it in both commits | Current source uses configuration and the page origin, but old copies remain in history |
| Stale dependency and setup guidance | Requirements named faster-whisper while source imports PyTorch and Transformers | Runtime requirements and README now match the implementation |
| Missing deployment controls | No authentication, upload limit, or transcript access control exists | Keep the prototype local and resolve these gaps before external deployment |
| Unresolved redistribution rights | No complete model, asset, or institutional permission record exists | Obtain permission and establish provenance before publication |

The original database and local artifacts remain unchanged.
No real lecture content or academic result was replaced with synthetic data.
New tests and README examples use explicitly synthetic data.

## Git state and scope

The reachable commits at review were `5b4c75e` and `6c55f98`, both dated 2026-05-16.
Their notices also use 2026, which supports the first-party copyright year.
No remote was configured at review time. This does not establish that the repository was never shared.

`E/` and `uploads/` contained no files at review time.
No notebooks, automated tests, lockfiles, package metadata, or vendored dependency trees existed in the original checkout.
The review added isolated tests, not a benchmark dataset.

## Completed source changes

- Added `.gitignore` rules for credentials, runtime data, bytecode, local environments, and legacy copies.
- Replaced the proprietary first-party notice with AGPL-3.0-only notices for Siddhant Tiwari.
- Added the unmodified official GNU AGPLv3 text from `https://www.gnu.org/licenses/agpl-3.0.txt`.
- Preserved institutional and academic attribution without asserting contributions by every listed team member.
- Added configuration through environment variables and removed the hard-coded private network address.
- Changed the launcher to bind to loopback and to require explicit TLS configuration.
- Made cross-origin browser access opt-in instead of allowing every origin with credentials.
- Removed routine logging of topic text, original upload filenames, course names, and malformed model responses.
- Replaced raw audio-processing exceptions in public API responses with generic errors.
- Corrected the health check to inspect the actual Transformers pipeline attribute.
- Corrected multipart headers in the shared browser upload helper.
- Escaped untrusted query parameters and error messages before inserting them as HTML.
- Replaced the survey's absolute anonymity claim with the actual behavior: no name or login is required.
- Added legal notices and `/license` and `/source` links to browser pages.
- Added an explicit allowlist for the source archive. It does not read Git history or include runtime files.
- Rewrote the README around the implementation and its limitations.

| Changed files | Purpose |
| --- | --- |
| `.gitignore` | Exclude sensitive data and local artifacts from future additions |
| `LICENSE`, `COPYRIGHT.md` | Provide the official license text and define first-party ownership and scope |
| `README.md` | Replace stale setup instructions with implementation-based documentation |
| `main.py` | Add configuration, safer launcher defaults, legal endpoints, and targeted API fixes |
| `audio_processor.py` | Add environment-based model selection and the current pipeline argument |
| `database.py` | Allow a separate database path for isolated runs |
| `nlp_engine.py` | Configure the model server and reduce lecture-content logging |
| `requirements.txt`, `requirements-dev.txt` | Match runtime imports, security floors, and test tools |
| `static/app.js`, `static/*.html` | Add legal notices, fix multipart headers, remove the private address, and escape selected untrusted text |
| `tests/test_*.py`, `tests/test_frontend.js` | Add isolated regression tests with synthetic data |
| `SECURITY.md`, `THIRD_PARTY_NOTICES.md`, `PUBLICATION_REVIEW.md` | Record privacy constraints, license review, evidence, and remaining actions |

These changes do not add authentication, validate model quality, or establish legal permission.
The source archive allowlist requires maintenance whenever source or build requirements change.

## Validation record

The validation environment uses Python 3.13.2 and Node.js 22.23.2.
A temporary virtual environment outside the repository inherits installed system packages, including PyTorch, to avoid a large runtime download.
This is not a clean-room installation or a reproducible dependency lock.

| Check | Result and scope |
| --- | --- |
| `python -m pytest -q -W error` | 42 tests passed using temporary databases and mocked model inference, with warnings treated as errors |
| `node --test tests/test_frontend.js` | Five tests passed for shared HTTP helpers, script syntax, notices, and selected escaping guards |
| `python -m pip check` | No broken requirements found in the validation environment |
| Resolved runtime dependency audit | pip-audit reported zero known vulnerabilities across 52 resolved packages, with no skipped package records |
| Source archive tests | Only explicit public files appear, license bytes match, and missing files and parent traversal return 503 |
| Launcher tests | Default bind address is loopback, original TLS files are not implicitly loaded, and incomplete TLS configuration fails |
| Python syntax and diff whitespace | All first-party Python files parse and `git diff --check` passes |
| Final heuristic privacy scan | No email, private-key marker, private network address, user-specific absolute path, or selected token format matched in 23 public text files |
| Ignore rules | All nine representative credential, runtime, and local-environment paths match ignore rules |
| Original artifact comparison | Git blob hashes match HEAD for the key, certificate, database, archive, and four original compiled files |
| Official license comparison | `LICENSE` matches the downloaded GNU text byte for byte |
| Git preservation | The index has no staged changes and both original commits remain intact |

The heuristic scan is not a certified secret scan and cannot establish that every possible sensitive value is absent.
Eight ignored artifacts remain tracked. Removing them from the index and addressing their history still require approval.

The dependency audit used an exact temporary inventory of the runtime dependency closure, including active extras and platform markers.
It did not treat the whole inherited Python installation as part of this application.
The first audit found vulnerable inherited dependencies and Transformers 4.x.
Requirements now select Transformers 5.x and impose security floors for affected runtime dependencies.
The speech pipeline uses the current `dtype` argument.
Zero reported vulnerabilities means no known matches in that audit, not proof that the software is secure.
Development-only dependencies and external Ollama, FFmpeg, and browser CDN contents were not included in that runtime audit.

Selected resolved versions:

```text
fastapi 0.162.2
uvicorn 0.54.0
starlette 1.10.0
python-multipart 0.0.33
requests 2.34.2
pydantic 2.13.4
torch 2.13.0
transformers 5.22.2
anyio 4.16.0
certifi 2026.10.23
filelock 4.2.9
setuptools 84.2.1
urllib3 2.8.0
```

Not verified: a clean installation, actual model downloads, real audio decoding, transcription quality, Ollama generation, GPU memory requirements, browser microphone interaction, and visual chart rendering.
The tests do not replace these checks.

## Required actions before publication

1. Treat the committed TLS key as compromised.
   Replace it and the corresponding certificate.
   Follow the issuer's revocation process if applicable.
   Review any reuse of that key or other credentials.

2. Keep a protected backup of the original database and any other private local data outside the release.
   Do not distribute them just because the source now carries AGPL notices.

3. Approve removal of the tracked artifacts from the Git index.
   The following is an example for the maintainer, not an operation performed by this review:

   ```bash
   git rm --cached -- key.pem cert.pem feedback_system.db E.zip
   git rm -r --cached -- __pycache__
   ```

   These commands leave local files in place but stage their removal.
   They do not remove any old commit, private contact detail, or historical network address.
   Review the staged diff before committing anything.

4. Decide how to prepare a public history.
   Either approve a carefully reviewed history rewrite in a separate clone, or publish a new repository from an explicit sanitized file selection.
   Review every branch, tag, commit message, author/committer identity, archive, and release that you intend to publish.
   Do not blindly copy the working directory or run `git archive HEAD` against the old history.
   If copies were already shared, address those copies separately.

5. Confirm ownership and institutional permission to publish the course submission.
   Resolve any copied-code or inline-asset attribution.
   Establish the selected model's origin and terms.
   See `THIRD_PARTY_NOTICES.md` for outstanding review items.

6. Perform a clean installation, resolve the exact dependencies, and rerun a current vulnerability audit.
   Exercise real FFmpeg decoding, Whisper transcription, and Ollama topic extraction with approved inputs.
   Test the browser recorder and charts, including trusted HTTPS if used remotely.

7. Inspect the final staged files and all intended public history with a secret scanner.
   Make sure that ignored runtime artifacts are no longer tracked.
   Never include raw scan output containing private values in a public report.

No commit, push, publication, index removal, history rewrite, or deletion of original artifacts was performed.
