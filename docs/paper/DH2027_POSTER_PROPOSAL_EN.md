# DH2027 poster proposal draft (not submission-ready)

**Working title:** Keeping Persian Cultural Knowledge Local: A Source-First Digital Humanities Demonstration  
**Target format:** Poster (the call specifies 500–750 words)  
**Target track:** Technical Track; consider Digital Arts only if the demonstrated work is framed and reviewed as a cultural/digital-art contribution  
**Status:** Draft for review. Literature references and the live-demo checklist must be completed before submission.

## Proposal

Digital cultural resources are increasingly accessed through general-purpose cloud services and generative systems whose answers can be difficult to trace back to a particular source. For Persian literary heritage, the practical challenge is not only whether an interface can produce fluent Persian, but whether a visitor can distinguish a retrieved poem or quotation from a model-generated interpretation, inspect where an answer came from, and continue to use the resource when an external service is unavailable. These are infrastructure and stewardship questions as much as interface questions. [Add references after reading work on digital cultural heritage stewardship, Persian text resources and retrieval-grounded language systems.]

This poster presents SIMORGH as a digital-humanities case study: a locally operated Persian knowledge interface that combines a small local language model with structured SQLite/FTS retrieval. The demonstration is designed around three observable actions rather than a product tour. First, a visitor asks who wrote a well-known Persian verse and sees whether the system can retrieve a candidate attribution from its local collection. Second, the visitor asks a source-oriented question and inspects the retrieved passage rather than treating the generated prose as a source. Third, the visitor asks for a fact that is not established by the available local material, allowing the demo to show whether the system acknowledges uncertainty instead of inventing a quotation or citation.

The technical contribution is a concrete demonstration of source-first interaction on commodity hardware, with clear separation between retrieval and model generation. The software repository includes an evaluation harness and an attribution component with explicit answer/uncertain/ambiguous outcomes. The poster will link to the public implementation and to a reproducibility note describing the exact version, model file hash, data hashes, machine configuration and evaluation conditions used in the demonstration. Those details will be supplied only after a fresh test run; this proposal makes no new performance or reliability claim.

The demo also makes a limitation visible. A retrieval system can only be as trustworthy as its collection, metadata and rights status. Some poetry attributions may be ambiguous or duplicated across poets, a local corpus can fail to load on a fresh clone, and a small language model can produce an incorrect answer when it has no useful evidence. The demonstration will therefore show source labels and abstentions alongside failures, not only successful queries. The current source and redistribution review records unresolved permissions for some embedded materials; the exhibition version must use data that the authors are entitled to display and must not distribute a dataset whose rights remain unclear.

This is relevant to digital humanities because it treats the interface, search index, attribution metadata and provenance record as part of the cultural artifact, rather than hiding them behind a generative response. It is also a technical sustainability question: a locally runnable tool can make collection-level behavior inspectable, while still requiring maintenance, documented dependencies and careful source stewardship. The demonstration does not claim that local execution alone guarantees accuracy, privacy, cultural authority or digital sovereignty. It offers a testable way to discuss those trade-offs with scholars, librarians, language technologists and the public.

The poster will present the retrieval/generation boundary, one successful retrieval, one ambiguity or failure case, and one abstention case. A QR code will point to the public source repository and the benchmark protocol. A short recorded walkthrough will be available in case the live environment fails. Before submission, the authors will verify that the demonstration can be run from a documented environment and will add a small set of relevant, read references, with citations that connect the technical method to existing digital-humanities and language-resource research.

## Before submission

- Replace every bracketed literature note with real sources read by the author.
- Confirm a working demo on the actual machine and save a backup recording; do not claim offline operation for any component not tested offline.
- Confirm which exact poetry/Quran data can lawfully be displayed.
- Re-check the DH2027 format, submission portal and deadline at the official call.
- Count 500–750 words in the final submission form; this draft is intended to be inside that range but must be counted after references and edits.
