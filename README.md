<!-- SPDX-FileCopyrightText: 2026 Siddhant Tiwari -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

# RIFT: IoT Anonymous Feedback System

RIFT is a course prototype that turns lecture audio into a topic-based comprehension survey.
It transcribes audio with Whisper through Hugging Face Transformers, extracts topics through Ollama, and stores ratings in SQLite.
A browser dashboard shows statistics for the latest lecture.

The project originated in AV321 Computer Networks at the Indian Institute of Space Science and Technology.
The repository contains the web application, not dedicated IoT device firmware.

Do not expose this application to the public internet. It has no authentication or access controls.
Do not publish the existing Git history until you resolve the blockers in [PUBLICATION_REVIEW.md](PUBLICATION_REVIEW.md).

## Features

- Record, pause, and upload microphone audio from a browser.
- Upload WAV, MP3, M4A, FLAC, OGG, or WebM files through the API.
- Provide an optional course name as context for topic extraction.
- Collect ratings from 1 to 10 without a name or login.
- Show response counts, average ratings, and population variance for each topic.
- Refresh the dashboard every 30 seconds or on demand.
- Display a normal-distribution approximation from each topic's average and variance.

The topic extractor requests 5 to 10 topics and limits each topic to five words.
The parser accepts fewer than five topics and truncates lists above ten.
The charts show self-reported comprehension, not measured learning outcomes.

## Architecture

```text
Browser recorder or multipart upload
    -> FastAPI -> Transformers Whisper -> transcript
    -> Ollama /api/generate -> topics
    -> SQLite sessions and topics

Student survey -> FastAPI -> SQLite feedback
Instructor dashboard -> FastAPI -> aggregate statistics -> Chart.js
```

Audio transcription uses `openai/whisper-large-v3` by default.
The default Ollama model identifier is `juilpark/gemma-4-26B-A4B-it-heretic:q4_k_m`.
This preserves the original selection, not an endorsement of its availability or licensing.
Review its source and terms, or select an approved model through `OLLAMA_MODEL`.

Uploaded audio uses a temporary file that the request handler deletes in its cleanup block.
An interrupted process can leave temporary files behind.
The database retains transcripts, topics, ratings, and timestamps.

## Prerequisites

- Python 3.11 or newer. The validation environment used Python 3.13.2.
- FFmpeg on `PATH` for decoding audio.
- Ollama with a locally installed model that you are entitled to use.
- Enough RAM and disk space for both models and their caches.
- A browser that supports microphone recording. Microphone access requires localhost or trusted HTTPS.

CUDA is optional. The audio processor uses CUDA with float16 when available and selected.
Otherwise, it uses the CPU with float32.
The source targets a high-memory GPU, but this release has no verified memory or latency measurements.
Do not rely on the previous README's 4 GB GPU guidance.

## Installation

Run commands from the repository root. The following shell examples use Bash.

1. Install FFmpeg through your operating system's package manager.
   On Ubuntu or Debian:

   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```

2. Install Ollama using its [official instructions](https://ollama.com/download).
   Review the selected model's license before downloading it.

3. Create and activate a Python environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell, use `.\.venv\Scripts\Activate.ps1` instead.

4. Install the Python dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

   For a specific CUDA version, install the matching PyTorch build using the
   [PyTorch instructions](https://pytorch.org/get-started/locally/) first.

5. Start Ollama in a separate terminal if it is not already running:

   ```bash
   ollama serve
   ```

6. Set and download your approved model:

   ```bash
   export OLLAMA_MODEL='REPLACE_WITH_APPROVED_MODEL_TAG'
   ollama pull "$OLLAMA_MODEL"
   ollama list
   ```

   Replace the placeholder before running these commands.
   The application does not download Ollama models automatically.
   Transformers downloads Whisper weights on first initialization unless they are cached.

## Configuration

Set environment variables before starting Python. The application does not load a `.env` file automatically.
Do not put credentials into source files or model server URLs.

| Variable | Default | Purpose |
| --- | --- | --- |
| `WHISPER_MODEL` | `openai/whisper-large-v3` | Transformers speech-recognition model |
| `WHISPER_DEVICE` | `cuda` | Use `cpu` to force CPU execution |
| `OLLAMA_MODEL` | Original model identifier listed above | Ollama model tag |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server, without a trailing API path |
| `RIFT_DATABASE_PATH` | `feedback_system.db` beside `database.py` | SQLite database file |
| `RIFT_UPLOAD_DIR` | `uploads/` beside `main.py` | Directory for temporary audio files |
| `RIFT_HOST` | `127.0.0.1` | Bind address for `python main.py` |
| `RIFT_PORT` | `8000` | Port for `python main.py` |
| `RIFT_SSL_KEYFILE` | Unset | Path to a new private TLS key |
| `RIFT_SSL_CERTFILE` | Unset | Path to its certificate |
| `RIFT_ALLOWED_ORIGINS` | Empty | Comma-separated browser origins allowed through CORS |

CORS controls cross-origin browser requests. It is not authentication.
Same-origin pages work without a CORS allowlist.
If you override the database path, create its parent directory first.
Use a new, empty database path for a demonstration instead of the original course database.

For a smaller speech model, set a compatible Transformers identifier, such as `openai/whisper-base.en`.
That alternative is not validated by the isolated tests.

## Run

```bash
python main.py
```

The default address is `http://127.0.0.1:8000`.
Startup initializes the database and attempts to load Whisper and connect to Ollama.
Startup can continue with an unavailable model, but audio processing will fail until its dependencies are ready.

| Interface | Path |
| --- | --- |
| Lecture recorder | `/record` |
| Student survey | `/student` |
| Instructor dashboard | `/dashboard` |
| Interactive API documentation | `/docs` |
| Component status | `/health` |
| License text | `/license` |
| Allowlisted first-party source archive | `/source` |

No frontend build step is required.
The dashboard loads Chart.js from a public CDN and therefore requires network access for charts.
For a remote microphone demonstration, configure trusted HTTPS and a restricted network before changing `RIFT_HOST`.
Set both TLS variables together. The launcher refuses incomplete TLS configuration.
It does not automatically reuse the original `key.pem` or `cert.pem`.

## API examples

Record only with the required consent. Use a recording that you have permission to process.

```bash
curl -X POST http://127.0.0.1:8000/upload-audio \
  -F 'file=@lecture.wav' \
  -F 'course_name=Computer Networks'

curl http://127.0.0.1:8000/topics/latest
```

The following response is illustrative synthetic data, not an inference result:

```json
[{"topic_id": 1, "topic_name": "Synthetic Topic", "session_id": 1}]
```

Use actual topic identifiers from your response when submitting feedback:

```bash
curl -X POST http://127.0.0.1:8000/submit-feedback \
  -H 'Content-Type: application/json' \
  -d '{"feedback":[{"topic_id":1,"rating":8}]}'

curl http://127.0.0.1:8000/dashboard-stats
```

| Method | Endpoint | Behavior |
| --- | --- | --- |
| `POST` | `/upload-audio` | Accept `file` and optional `course_name` as multipart data |
| `GET` | `/topics/latest` | Return the latest session's topics, or 404 |
| `POST` | `/submit-feedback` | Accept 1 to 10 ratings, each from 1 to 10 |
| `GET` | `/dashboard-stats` | Return latest-session counts, means, and population variances, or 404 |
| `GET` | `/session/{session_id}` | Return a stored session, including its complete transcript |
| `GET` | `/health` | Return database, audio processor, and Ollama status |

Application-generated HTTP errors use an `error` field.
Request validation errors use FastAPI's `detail` format.
An overall healthy status only establishes that the database query succeeded.
Read the component fields to assess inference readiness.

## Repository layout

```text
main.py                   FastAPI routes and launcher
audio_processor.py        Transformers speech recognition
database.py               SQLite schema and queries
nlp_engine.py             Ollama requests and topic parsing
static/                   Recorder, survey, charts, and shared JavaScript
tests/                    Isolated Python and Node.js tests
requirements.txt          Runtime dependency bounds
requirements-dev.txt      Test and dependency-audit tools
LICENSE                   Official GNU AGPLv3 text
COPYRIGHT.md              First-party licensing scope and academic context
THIRD_PARTY_NOTICES.md     Dependency and model license review
SECURITY.md               Privacy and deployment constraints
PUBLICATION_REVIEW.md     Release blockers and validation record
```

The database contains `sessions`, `topics`, and `feedback` tables.
Each topic belongs to a session. Each feedback row contains a topic identifier, rating, and timestamp.
No recordings or datasets are required in the public repository.

## Tests and reproducibility

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node --test tests/test_frontend.js
```

Node.js 20 or newer is required only for JavaScript tests.
The tests use synthetic data, temporary databases, and mocked model responses.
They do not download weights, contact Ollama, or change the original database.
They do not establish real transcription quality, hardware requirements, or model availability.

Dependencies use bounded version ranges, not a lockfile.
Record the resolved package versions, model revisions, hardware, and input consent before comparing experimental results.
No verified accuracy, throughput, or learning-outcome benchmark accompanies this release.
See [PUBLICATION_REVIEW.md](PUBLICATION_REVIEW.md) for validation details.

## Limitations and troubleshooting

- No authentication, authorization, rate limiting, or duplicate-submission prevention exists.
  Anyone with access can submit ratings, upload audio, and retrieve stored transcripts.
- The database omits student names, but timestamps and web server logs can identify activity.
  This is not a guarantee of anonymity.
- Upload validation checks the extension and file size, not the decoded audio content.
  The server reads the full upload into memory and does not enforce a hard size limit.
- Inference uses blocking work inside an async route. Long requests can block other clients.
- SQLite foreign-key enforcement is not enabled. Feedback can reference a nonexistent topic.
- The dashboard's student count is the maximum per-topic response count, not a count of unique people.
- The normal-distribution chart estimates percentages from aggregate statistics.
  It is not a histogram of actual responses. A zero variance uses a display variance of 0.2.
- The speech processor accepts VAD arguments, but does not implement voice activity detection.
- Topic prompts truncate transcripts after 300,000 characters. Model context limits can be lower.
- The Chart.js CDN URL is unpinned. Review and pin or vendor it before an external deployment.

If Ollama is unavailable, start the service and make sure that `ollama list` includes the configured tag.
If audio decoding fails, make sure that `ffmpeg -version` works in the same terminal.
If GPU memory runs out, select a smaller approved model or set `WHISPER_DEVICE=cpu`.
If microphone access fails, use localhost or trusted HTTPS and allow microphone access in the browser.

## Contributing and licensing

Keep changes focused, document API changes, and run the isolated tests.
Use synthetic fixtures and never include recordings, transcripts, credentials, or private correspondence in a contribution.
Update the explicit `SOURCE_FILES` list in `main.py` when adding first-party source or build instructions.

Author and first-party copyright holder: Siddhant Tiwari.
Academic context and original team attribution appear in [COPYRIGHT.md](COPYRIGHT.md).
Dependencies and model providers retain their own rights and licenses.

Eligible first-party work uses [GNU AGPL-3.0-only](LICENSE), without warranty.
If you modify the application and provide remote network access, comply with the source-offer requirements in section 13.
The built-in `/source` route serves only explicitly listed public files, never runtime data or Git history.
Do not treat the license change as permission to distribute third-party or restricted course material.
