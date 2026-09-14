# SIMORGH Privacy and Data-Flow Map

Status: engineering baseline, not legal advice.

This map describes the current repository architecture so deployment-specific privacy documentation can be derived from executable behavior. It does not by itself establish a lawful basis, controller/processor role, retention period, or jurisdictional compliance.

## Data surfaces

| Surface | Data handled | Default location | Retention behavior | External transfer | Status |
|---|---|---|---|---|---|
| Chat input | User question and generated response | Local SQLite memory DB | Persists when API endpoint stores conversation | Local LLM only by default | IMPLEMENTED / review deployment context |
| Session identifier | Client-provided opaque session token | Hashed before memory storage | Persists with conversation rows | None by default | IMPLEMENTED |
| Provenance memory | Content, source, confidence, status, timestamps | `memory/provenance.db` | Persists until operator/user deletes DB or a future retention control is applied | None by default | IMPLEMENTED |
| Logs | Application/runtime logs | `logs/` | Operational retention not yet enforced | None by default | P1 |
| Voice input | Raw PCM request body | Temporary WAV under runtime audio directory | Deleted in `finally` after transcription | None by default unless STT implementation/provider changes | IMPLEMENTED / verify STT provider |
| Voice output | Generated WAV | `audio_out/` | File lifecycle currently runtime-dependent | None by default | P1 |
| Imported documents | Uploaded/imported content | Configurable import directory | Lifecycle depends on importer/storage path | None by default | P1 |
| Local model prompts | System prompt + user message | Local llama-compatible endpoint by default | Controlled by local model server | No mandatory cloud transfer | IMPLEMENTED / runtime-dependent |
| Optional external providers | User prompts and provider responses if explicitly configured | Provider-controlled | Provider policy | Yes, opt-in | EXPERIMENTAL / deployment contract required |

## Current protections

- Local mode defaults to loopback binding.
- Non-loopback binding without `SIMORGH_KEY` fails closed.
- External binding requires `x-token` for non-health requests.
- Session identifiers are hashed before memory storage.
- Voice input is size-limited and raw voice input is removed after processing.
- Voice endpoint no longer places user text or model response text in response headers.
- API responses advertise AI-generated output on generation endpoints.
- Local-first operation does not require a cloud account or API key.

## Required deployment decisions before handling personal data at scale

1. Identify controller/processor roles and applicable jurisdiction.
2. Define lawful basis and purpose for each personal-data surface.
3. Define retention and deletion periods for memory, logs, imports, and outputs.
4. Document data-subject rights and operational response procedures.
5. Decide whether any external model/provider receives personal data.
6. Establish transfer mechanisms for cross-border processing where required.
7. Conduct a DPIA or equivalent risk assessment when the processing is likely to create high risk.
8. Define breach detection, response, notification, and evidence-preservation procedures.
9. Define child/minor handling and age-appropriate safeguards before targeting or knowingly serving minors.
10. Publish user-facing privacy documentation that matches executable behavior.

## Design rule

The implementation must never silently claim that local-first means no personal-data processing. Local storage is still processing. External providers are optional, not automatically harmless. A deployment is compliant only when the concrete processing, purposes, rights, safeguards, contracts, and jurisdictional requirements have been assessed.
