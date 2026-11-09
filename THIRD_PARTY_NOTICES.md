<!-- SPDX-FileCopyrightText: 2026 Siddhant Tiwari -->
<!-- SPDX-License-Identifier: AGPL-3.0-only -->

# Third-party components and licensing scope

The AGPL-3.0-only notice covers eligible first-party work, not third-party components.
Dependencies retain their own licenses. Model weights and recordings require separate permission.
This document is an inventory and review guide, not a legal clearance certificate.

## Python dependencies

The following license identifiers come from installed package metadata in the validation environment.
Consult each resolved distribution's license files for the complete terms and bundled notices.

| Component | Declared license | Role |
| --- | --- | --- |
| FastAPI | MIT | Web API |
| Starlette | BSD-3-Clause | Web framework dependency |
| Uvicorn | BSD-3-Clause | ASGI server |
| python-multipart | Apache-2.0 | Multipart parsing |
| Requests | Apache-2.0 | Ollama HTTP client |
| Pydantic | MIT | Request and response validation |
| Transformers | Apache-2.0 | Speech-recognition pipeline |
| PyTorch | Multiple licenses, listed below | Tensor execution |
| pytest | MIT | Development tests |
| HTTPX | BSD-3-Clause | Development API tests |

The installed PyTorch package declares:

```text
Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT
```

Do not replace this expression with a single first-party license.
Other transitive dependencies also carry their own notices.
The dependency audit described in `PUBLICATION_REVIEW.md` checks known vulnerabilities, not license compatibility.
No third-party source tree or model weights are intentionally bundled in the public release.
If you redistribute wheels, containers, executables, or dependencies, include their required notices and review the exact distribution.

## Browser dependencies and assets

The dashboard and topic-details page load Chart.js from
`https://cdn.jsdelivr.net/npm/chart.js`.
The URL does not pin a version. Chart.js upstream uses the MIT license.
Before external deployment, pin a reviewed version and preserve its license notice if you vendor it.
See [Chart.js upstream](https://github.com/chartjs/Chart.js).

The pages contain inline SVG icons and a numerical approximation for the error function.
The repository provides no separate provenance record for these snippets.
Confirm that they are original work or add the required upstream notices before publication.
Do not infer ownership from the absence of a header.

## Model weights and services

- `openai/whisper-large-v3` is the configured speech model.
  Review the [model card](https://huggingface.co/openai/whisper-large-v3) and the exact revision before use or redistribution.
- `juilpark/gemma-4-26B-A4B-it-heretic:q4_k_m` is the preserved original Ollama model identifier.
  Its availability, upstream lineage, weight license, and redistribution terms are not established by this repository.
  Do not assume that a model served through Ollama uses Ollama's software license or AGPL.
- Ollama and FFmpeg are external system tools, not first-party repository code.
  Their licenses and the FFmpeg build configuration need separate review if you distribute them.

Selecting a replacement model does not automatically resolve its licensing obligations.
Record the model source, revision, terms, and any attribution required for a release.

## Course material and runtime data

The legacy archive, recordings, transcripts, feedback, and local certificates are excluded from the intended release.
The AGPL notice does not grant rights over other people's speech or personal data.

Keep written permissions and private correspondence outside the public repository.
Confirm institutional rules for publishing course submissions and any course-provided code.
No incompatible third-party license was conclusively established during this review, but the unresolved provenance and model terms prevent full clearance.
