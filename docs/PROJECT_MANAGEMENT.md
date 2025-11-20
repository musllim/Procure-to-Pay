# Project Management Guidelines — Procure-to-Pay Mini System

Reference: `docs/SRS.md`

Purpose
- Provide a compact, actionable project management guide for implementing the Procure-to-Pay mini system described in the SRS. This document lists features, requirements, acceptance criteria, priorities, milestones, risks and basic QA checks to track progress toward the Nov 26 deadline.

1. Features (high level)
- Feature 1: Authentication & Role Management
  - Description: JWT-based authentication, role assignment (`staff`, `approver_level_1`, `approver_level_2`, `finance`, `admin`), admin panel for user/role management.
  - Priority: High
  - Owner: Backend
  - Acceptance Criteria: Users can log in via token auth; roles enforced server-side; admin can assign roles.

- Feature 2: Purchase Request CRUD
  - Description: Staff can create/update/list/view purchase requests with items and optional proforma upload.
  - Priority: High
  - Owner: Backend + Frontend
  - Acceptance Criteria: `POST /api/requests/` creates PR with items; staff sees own PRs; updates allowed only when status=PENDING.

- Feature 3: Multi-level Approval Workflow
  - Description: Level-based approvals (configurable), approvers can approve/reject, approval history stored.
  - Priority: High
  - Owner: Backend + Frontend
  - Acceptance Criteria: Approvers use `/api/requests/{id}/approve/` and `/reject/`; any rejection sets PR to `REJECTED`; final approval creates a `PurchaseOrder` record.

- Feature 4: Purchase Order Generation
  - Description: Auto-generate PO when last approval is granted, produce a downloadable PO document.
  - Priority: High
  - Owner: Backend
  - Acceptance Criteria: PO record exists for PR after final approval; `GET /api/purchase-orders/{id}/download/` returns a PDF.

- Feature 5: Receipt Upload & Validation
  - Description: Staff uploads receipts; system extracts data and compares with PO; discrepancies flagged for finance.
  - Priority: Medium-High
  - Owner: Backend + Frontend
  - Acceptance Criteria: Receipt file accepted for approved PRs; automated validation produces `MATCHED` or `DISCREPANCY` status saved on `Receipt` record.

- Feature 6: Document Processing (Proforma/Receipt)
  - Description: Use PDF parsing + OCR (+ optional LLM) to extract structured data from uploaded documents.
  - Priority: Medium
  - Owner: Backend
  - Acceptance Criteria: For sample uploads, extracted JSON contains vendor, items (name, qty, price) and totals for >80% accuracy on supplied test samples.

- Feature 7: Finance Dashboard
  - Description: Web UI for finance to view approved PRs/POs, download attachments, upload invoices and resolve discrepancies.
  - Priority: Medium
  - Owner: Frontend
  - Acceptance Criteria: Finance role can list filtered POs, download attachments, and mark discrepancy handled.

- Feature 8: API Documentation & Deployment
  - Description: Provide Swagger/OpenAPI or Postman collection; Dockerized app; public deployment URL.
  - Priority: High
  - Owner: Backend/DevOps
  - Acceptance Criteria: API docs served at `/api/docs/` and raw schema at `/api/schema/`; `docker-compose up --build` runs locally; live URL provided in README.
  - Documentation Requirements: The OpenAPI/Swagger docs must include, per-route, the HTTP method, request/response schemas, authentication requirement, and required role(s). The Swagger UI must support trying endpoints with JWT auth.

2. Requirements (condensed from SRS)
- Functional: authentication & RBAC; PR create/update/list/view; approval endpoints; PO generation; file uploads; document extraction; receipt validation.
- Non-functional: pagination, performance targets, security (HTTPS, env secrets), logging, DB transactions for concurrency, file size/type validation.

3. Acceptance Criteria (per feature) — checklist form
- Authentication
  - [ ] Token login returns access token
  - [ ] Endpoints require authentication by default
  - [ ] Role-based access enforced for approval/finance endpoints

- PR CRUD
  - [ ] Create PR (with items + optional proforma file)
  - [ ] Staff lists only own PRs
  - [ ] PUT updates only when PR.status == PENDING

- Approvals
  - [ ] Approve endpoint writes Approval record
  - [ ] Reject endpoint requires a reason and marks PR.REJECTED
  - [ ] Concurrent approvals handled without race conditions (DB transaction/locking)

- PO generation
  - [ ] PO created automatically when final approval occurs
  - [ ] PO contains vendor, items, totals, and link to PR

- Receipt & Validation
  - [ ] Receipt upload accepted only for APPROVED PRs
  - [ ] Extraction populates `Receipt.extracted_data`
  - [ ] Validation compares items and totals and sets `validation_result`

- Docs & Deployment
  - [ ] Swagger or Postman collection included in repo
  - [ ] Dockerfile and docker-compose enable local build and run
  - [ ] Public URL documented in README

4. Milestones & Timeline (suggested)
- Day 1 (today): finalize SRS (done), scaffold backend (done), create PM guideline (this doc).
- Day 2: Implement data models, serializers, and basic PR endpoints (create/list/get). Run migrations and seed sample data.
- Day 3: Implement approval endpoints, Approval model, PO generation logic, and tests for concurrent approvals.
- Day 4: Implement proforma upload + basic document extraction pipeline (sync or Celery stub) and receipt upload endpoint.
- Day 5: Build minimal frontend views for staff and approver flows (login, create PR, list, detail, approve/reject).
- Day 6: Finance dashboard, validation UI, Swagger docs, Docker polish, deploy to chosen host, and final testing.

Target: complete end-to-end happy path and deploy a public instance by Nov 26. Reserve 1 day buffer for deployment/CI issues.

5. Sprint / Task Breakdown (example tasks for Day 2-3)
- Task A: Implement models (PR, RequestItem, Approval, PO, Receipt, Document) — Backend
- Task B: Implement serializers & viewsets for PR CRUD — Backend
- Task C: Add router & endpoints, add health-check and basic permission classes — Backend
- Task D: Unit tests for models and PR endpoints — Backend
- Task E: Implement approval actions with DB transactions and tests for concurrency — Backend

6. QA / Test Cases (smoke tests)
- Smoke 1: Health-check returns 200
- Smoke 2: Create PR with 2 items and proforma; GET PR by ID returns items and proforma link
- Smoke 3: Approver A (level 1) approves; PR remains PENDING; Approver B (level 2) approves; PR becomes APPROVED and PO exists
- Smoke 4: Upload receipt for approved PR; validation job runs and sets `validation_result`

7. Risks and Mitigations
- OCR/LLM accuracy: mitigate by providing manual edit UI for extracted data and keep heuristic fallback parsers.
- Concurrency: mitigate with DB transactions and select_for_update before status mutation; add tests that simulate concurrent approvers.
- Deployment delays: use managed services (Render/Fly) to speed up deployment; keep local Docker workflow working.

8. Definition of Done (per feature)
- Code merged to `main` with passing unit tests for backend change.
- API documented and includes example requests.
- Docker compose runs locally and migrations complete.
- Demo instance reachable at public URL and credentials/README included.

9. Deliverables (repo contents)
- `procure_to_pay/` Django project, `p2p/` app with models, serializers, views and migrations
- `docs/SRS.md`, `docs/PROJECT_MANAGEMENT.md`
- `requirements.txt`, `Dockerfile`, `docker-compose.yml`
- Frontend folder (when implemented) with build & usage notes
- Postman collection or OpenAPI spec

10. Owners & Contacts
- Developer / Implementer: (you)
- Evaluation / Review: IST Africa contacts listed in SRS

11. Notes
- Keep PR titles, commit messages and README updated to reflect deployed URL and demo credentials.
- Break work into small PRs and run tests locally before merging. Use the tasks above to create GitHub issues.

---
Last updated: 2025-11-20
