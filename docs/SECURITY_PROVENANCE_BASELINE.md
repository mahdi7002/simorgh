# SIMORGH Security & Provenance Baseline

This document records the current engineering baseline for safe automation,
data provenance, and human accountability. It is an implementation policy,
not a claim that SIMORGH is certified under any external framework.

## 1. Human authority

SIMORGH may propose, analyze, test, stage, and report changes. It must not
silently change code, models, capabilities, architecture, scope, or canonical
user data without the explicit human gate defined by `docs/CHARTER.md`.

Automation must be split into:

- read-only inspection;
- isolated staging/build/evaluation;
- explicit apply/release;
- post-apply verification.

This preserves the project's existing governing constraint while reducing
approval fatigue through bounded automation rather than unrestricted autonomy.

## 2. Filesystem and network boundaries

Agentic or automated execution should use two independent boundaries:

- filesystem access is limited to the workspace and explicitly approved data;
- network access is denied by default and opened only for named, necessary
  sources such as a pinned Ganjoor snapshot.

A network exception never implies permission to read unrelated local secrets,
and filesystem access never implies unrestricted network egress.

## 3. Least-privilege CI

GitHub Actions must default to the minimum permissions needed by the workflow.
Read-only verification workflows use `contents: read` and disable checkout
credential persistence where practical. Workflows that do not publish releases
must not request write permissions merely for convenience.

## 4. Immutable provenance

External data used to construct a canonical artifact must be anchored to:

1. source repository;
2. exact immutable commit/ref;
3. source manifest counts where available;
4. deterministic reconstruction rules;
5. resulting artifact hash or other verifiable identity.

For the current poetry rebuild, the Ganjoor anchor is:

`ganjoor/ganjoor-data@a64968e78425b2e8c7904fbdf5289fba8251a757`

The manifest reports 240 poets and 135,319 poems for that snapshot.

## 5. Verify the claim, not just the build

A successful build is insufficient. The rebuild process must separately verify:

- every expected source poem file was parsed;
- no source files were silently dropped;
- no content-based deduplication altered corpus cardinality;
- no length limit altered the canonical corpus;
- every SQLite row carries source provenance;
- SQLite integrity passes;
- FTS is rebuilt and its row coverage is checked;
- source JSON and SQLite values match under the documented reconstruction
  mapping.

`verify_ganjoor_rebuild.py` provides the independent corpus comparison gate.

## 6. Canonical corpus versus runtime limits

Canonical source data must not be truncated merely to satisfy prompt, UI, or
model-context limits. Those limits belong to runtime consumers. A long poem is
still a valid corpus record unless the source itself says otherwise.

Therefore the complete Ganjoor rebuild defaults to `--max-chars 0`.

## 7. Backup and atomic apply

Canonical replacement must be staged first. Before `--apply`, the existing
canonical database is copied to a timestamped backup. Replacement is performed
through a temporary file and atomic rename. Post-apply integrity and count
checks are mandatory.

## 8. Rights are a separate gate

Provenance does not establish redistribution permission. Public availability of
an upstream repository is not treated as a license grant. `ASSET_RIGHTS.csv`
remains the authority for the project's human rights review and must not be
changed to VERIFIED without evidence for the exact asset and jurisdiction.

## 9. Supply-chain provenance

For release artifacts that people are expected to consume, SIMORGH may use
GitHub artifact attestations/Sigstore provenance and an SBOM. Attestation is
not treated as proof of safety by itself; the consumer-facing policy must still
verify the artifact and evaluate the claimed source/build context.

Routine test runs need not generate attestations merely to create noise. The
provenance control belongs where an artifact becomes a distributed trust
boundary.

## 10. Practical decision rule

When a newer automation capability conflicts with human authority, choose the
bounded option:

`inspect -> stage -> evaluate -> explicit human apply -> verify -> record provenance`

Never:

`agent decides -> agent changes canonical state -> agent declares success`

## External engineering references

- GitHub Actions artifact attestations and provenance:
  https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations
- GitHub artifact attestation concepts:
  https://docs.github.com/en/actions/concepts/security/artifact-attestations
- Anthropic Claude Code sandboxing:
  https://www.anthropic.com/engineering/claude-code-sandboxing
- Anthropic Claude Code permission/approval model:
  https://www.anthropic.com/engineering/claude-code-auto-mode
- NIST AI Risk Management Framework:
  https://www.nist.gov/itl/ai-risk-management-framework
