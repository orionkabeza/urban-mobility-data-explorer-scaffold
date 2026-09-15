# AI Usage Disclosure

Tool: Claude Code
Session date: 2026-09-15
Requested by: Orion Kabeza (o.kabeza@alustudent.com)

## Scope of AI involvement

One task: regenerating `docs/database_design.pdf` after a teammate updated
`docs/erd_diagram.png` but the PDF still embedded the outdated diagram.

## What happened

The assistant inspected the repository and found that `docs/erd_diagram.png`
had been updated in commit `20ec069` ("adding final change on erd diagram"),
but `docs/database_design.pdf` still dated from the earlier commit `e504fdf`
— the PDF was stale, not the underlying content. It rebuilt the PDF from the
existing, already human-authored `docs/database_design.md` (no text content
changes) using Python's `markdown` and `xhtml2pdf`, matching the original
PDF's toolchain (confirmed via the original file's embedded metadata:
`Producer: xhtml2pdf`). Output was verified by rendering pages to images and
visually checking that the updated ERD and all tables displayed correctly
(14 pages, no broken content).

## What AI did not do

The assistant did not design the ERD entities or relationships, write any
DDL/SQL, author the JSON schemas, or write the design-rationale prose in
`docs/database_design.md`. Those deliverables are attributable to individual
team member commits:

| Deliverable | Author | Commit |
|---|---|---|
| Repo scaffold, README, architecture diagram (Week 1) | Orion Kabeza | `485ec41`, `d8fb3d0` |
| ERD design, SQL schema, JSON examples, design doc (first pass) | Orion Kabeza | `e504fdf` |
| Transactions/participants schema refinements | Emmanuel Rangira | `d16bcc0` |
| Users table + paginated JSON example | Kenneth Master | `1314ede` |
| System_logs schema (run_id, dead-letter check) | Djibril Mpamira | `23c4efe` |
| `is_active` column, final ERD image revision | Aubin Mfura | `3194952`, `20ec069` |
| `database_design.pdf` regeneration (mechanical rebuild, no design content) | Claude Code | `a06ebd4` |

## Caveats

This disclosure covers only this session. It does not attest to whether
other team members used AI tools on their own machines for their
commits — each member's own contribution should be disclosed by them if
their course requires it.
