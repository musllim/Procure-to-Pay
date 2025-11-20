# Software Requirements Specification (SRS)

Project Title: Procure-to-Pay — Mini Purchase Request & Approval System

Purpose
- Provide a clear specification for implementing a simplified Procure-to-Pay system for the IST Africa technical assessment.
- The system enables staff to submit purchase requests and receipts, multi-level managers to approve/reject, and finance to access approved requests. The system supports document processing (proforma/receipt extraction) and automatic PO generation.

Stakeholders
- Applicant / Developer
- IST Africa Recruitment Team (evaluators)
- Staff users (submit requests)
- Approvers (level-1, level-2)
- Finance team (view/manage POs and receipts)
- System administrators / DevOps

Scope
- Backend: Django + Django REST Framework APIs implementing the full workflow, RBAC, file upload, document processing triggers, PO generation.
- Frontend: React with login, dashboards, request form, list, detail, approval UI, receipt upload.
- Containerization: Docker + docker-compose for local development; deployment to a public host (Render, Fly.io, AWS EC2, or similar).
- AI/Document processing: proforma/receipt text extraction via PDF parsing + OCR + optional LLM to parse/extract structured data.

Definitions / Acronyms
- PR: Purchase Request
- PO: Purchase Order
- OCR: Optical Character Recognition
- LLM: Large Language Model
- RBAC: Role-Based Access Control

Functional Requirements

1. Authentication & Authorization
- Users must authenticate using JWT (recommended) or token-based auth.
- Role types: `staff`, `approver_level_1`, `approver_level_2`, `finance`, `admin`.
- RBAC enforced server-side; frontend shows UI appropriate to role.

2. Purchase Request Management (core)
- Staff can create a Purchase Request via `POST /api/requests/` with fields: `title`, `description`, `amount`, optional `proforma` (file), optional `items` list.
- Request initial status: `PENDING`.
- Staff can `GET /api/requests/` to list their requests (staff sees only own unless role permits).
- Staff can `PUT /api/requests/{id}/` to update pending requests only (not after approval/rejection).
- Staff can `POST /api/requests/{id}/submit-receipt/` with receipt file and metadata.

3. Approval Workflow
- Multiple approval levels (configurable; default: 2 levels). A `PurchaseRequest` may require approvals from level-1 and level-2 approvers.
- Approvers view pending requests via `GET /api/requests/?status=pending` (filtered by level if necessary).
- Approver can `PATCH /api/requests/{id}/approve/` to approve (with optional comment).
- Approver can `PATCH /api/requests/{id}/reject/` to reject (with required reason).
- Any rejection sets request status to `REJECTED` permanently.
- All required approvals set status to `APPROVED` permanently.
- Once `APPROVED` or `REJECTED` status is set, it cannot be changed (immutability).
- Last approval triggers automatic Purchase Order generation.

4. Purchase Order Generation
- When last required approval happens, system auto-generates a `PurchaseOrder` record and optionally a downloadable PO document (PDF).
- PO contains vendor, items, prices, payment terms, reference to PR and approver(s).

5. Receipt Submission & Validation
- Staff uploads receipt via `POST /api/requests/{id}/submit-receipt/`.
- System extracts receipt data and validates against the generated PO (items, prices, vendor). Returns validation results and flags discrepancies.
- Finance receives flags and can mark the receipt as `MATCHED` or `DISCREPANCY_HANDLED`.

6. Document Upload & Processing
- Proforma/quotation upload during request creation or update. File stored and processed.
- Automatic extraction: parse proforma to pull vendor, items (name, qty, unit price), total, terms.
- For PDF/scans, use `pdfplumber`/`PyPDF2` for text PDFs and `pytesseract` for scanned images.
- Optional LLM step: pass extracted raw text to a prompt that returns structured JSON for complex layouts.

7. Concurrency & Consistency
- System must safely handle concurrent approvals (optimistic locking or database transactions).
- Prevent race conditions where two approvers simultaneously think they are the last approver. Use DB transactions and row-level checks before changing status.
- File uploads must be atomic and associated transactionally with PRs where possible.

8. Admin/Finance UI
- Finance can view all approved PRs and POs, download attachments, upload invoice/receipt files, and export lists (CSV).
- Filters and pagination for lists (status, date range, amount range, created_by).

9. Notifications (optional)
- Email notifications for approval/rejection (configurable). If implemented, use background task worker (Celery + Redis).

API Documentation
- Provide API docs (Swagger/OpenAPI or Postman collection) at `/api/docs/` or as repo artifact.

Non-Functional Requirements

1. Performance & Scalability
- List endpoints paginated (default page size 20).
- Response time for typical API calls < 300ms under normal load.
- Document processing is asynchronous (long-running), notify via status or webhook.

2. Security
- Use HTTPS in deployment. Store secrets in env vars.
- Enforce RBAC and permission checks server-side; never trust frontend role info.
- File uploads: validate types and size limits (e.g., max 10MB default), scan for malicious files.
- Protect against common web vulnerabilities (CSRF, XSS, SQL injection). For APIs, use JWT + CORS policy.
- Audit trail: store who performed approvals and timestamps.

3. Reliability & Data Integrity
- Use PostgreSQL for persistent storage, with DB transactions for status changes.
- Backups: document recommended backup strategies (DB dumps, S3 for files).

4. Observability
- Logging for key events (request created, approved, rejected, PO generated, receipt validation results).
- Expose basic metrics (requests count, approval rates) optionally via Prometheus.

5. Maintainability
- Clean code structure, tests, clear README, and API docs.
- Provide Dockerfile and `docker-compose.yml` to run Postgres + app locally.

Data Model (high level)

- User (Django User or custom)
  - Fields: `username`, `email`, `first_name`, `last_name`, `role` (enum), is_active, etc.

- PurchaseRequest
  - id, title, description, amount (Decimal), currency, status (PENDING/APPROVED/REJECTED), created_by (FK User), current_level (int), required_approval_levels (int), created_at, updated_at, proforma (FileField), purchase_order (FK optional), receipt (FK optional)

- RequestItem (optional, but recommended)
  - id, purchase_request (FK), description, quantity (int), unit_price (Decimal), total_price

- Approval
  - id, purchase_request (FK), approver (FK User), level (int), action (APPROVED/REJECTED), comment, created_at

- PurchaseOrder
  - id, PR (FK), vendor_name, items (JSON or M2M via POItem), total_amount, po_number, generated_by (system user/admin), generated_at, po_document (FileField)

- Receipt
  - id, PR (FK), uploaded_by, file, extracted_data (JSON), validation_result (MATCHED/DISCREPANCY/UNVALIDATED), notes, created_at

- Document (generic, optional)
  - id, owner (FK), type (proforma/receipt/other), file, extracted_data, processed_at, status

REST API Endpoints (spec examples)

- Authentication
  - POST /api/auth/login/ → request: {username,password}; response: {access_token, refresh_token}
  - POST /api/auth/refresh/ → refresh JWT

- Purchase Requests
  - POST /api/requests/  
    - Roles: staff  
    - Body: {title, description, amount, currency, items[], proforma (multipart)}  
    - Response: 201 with PR data
  - GET /api/requests/  
    - Roles: staff (own), approver (pending/assigned), finance (all approved)  
    - Query params: `status`, `created_by`, `page`, `page_size`, `min_amount`, `max_amount`, `date_from`, `date_to`  
    - Response: paginated list
  - GET /api/requests/{id}/  
  - PUT /api/requests/{id}/  
  - PATCH /api/requests/{id}/approve/  
  - PATCH /api/requests/{id}/reject/  
  - POST /api/requests/{id}/submit-receipt/  
  - GET /api/requests/{id}/history/  

- Purchase Orders
  - GET /api/purchase-orders/ (finance)  
  - GET /api/purchase-orders/{id}/download/ → returns PO document

- Document Processing
  - GET /api/documents/{id}/extraction/ → returns extracted JSON
  - POST /api/documents/validate/ → validate doc against PO (used internally)

- Admin
  - GET /api/users/ (admin)  
  - POST /api/roles/assign/

Validation & Error Handling
- Return 400 for invalid input, 403 for unauthorized, 404 for not found, 409 for conflicting operations (e.g., PR already approved).
- For concurrency, return 409 when operation cannot proceed due to state change and provide current resource state in response.

Sequence / Workflow Diagrams (textual)

- PR Creation:
 1. Staff submits PR with optional proforma.
 2. Server stores PR, enqueues doc processing job to extract proforma data.
 3. Approvers receive PR in pending queue.

- Approval Flow:
 1. Approver (level N) fetches pending PR.
 2. Approver calls `/approve/` or `/reject/`.
 3. Server transactionally verifies current status & required approvals.
 4. If approve and all levels done → set PR `APPROVED`, create PO record, generate PO document.
 5. If reject → set `REJECTED`, notify staff.

- Receipt Validation:
 1. Staff uploads receipt.
 2. Server enqueues OCR/parsing job.
 3. Parsing extracts items/vendor/amounts then compares with PR/PO.
 4. Validation results stored and returned; finance notified if discrepancy.

Document Processing Design

- Architecture:
  - Synchronous API to accept files and enqueue asynchronous worker (Celery + Redis) to run extraction (PDF parsing + OCR).
  - Use `pdfplumber`/`PyPDF2` for text PDFs. Use `pytesseract` for image-based PDFs.
  - Normalization: Extract raw text → LLM/heuristic parser to map to structured fields (vendor, items, qty, unit_price, totals).
  - Save `extracted_data` JSON in `Document`/`Receipt`.

- Tools & Libraries:
  - `pdfplumber`, `PyPDF2`, `pytesseract`, `Pillow`, optional OpenAI or local LLM via API for parsing ambiguous layouts.

- PO PDF generation:
  - Use a templating engine (WeasyPrint or ReportLab) to create simple PO PDF from database fields.

Concurrency & Data Integrity Implementation Notes

- Use DB transactions around approval operations. Example:
  - In DRF view: start transaction, SELECT PurchaseRequest FOR UPDATE, check status & approvals, write Approval record and update PR status, commit.

Storage & File Handling

- Development: store files on disk (e.g., `MEDIA_ROOT`) via Django `FileField`.
- Production: use S3-compatible storage (AWS S3) and serve via signed URLs.
- Limit file size and allowed mime types. Virus scanning optional.

Deployment & Docker

- Provide:
  - `Dockerfile` for Django app.
  - `docker-compose.yml` with services: `web` (Django), `db` (Postgres), `redis` (optional for Celery), `worker` (Celery).

- Environment:
  - Use env vars for `DJANGO_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `ALLOWED_HOSTS`.

- Public deployment:
  - Option 1 (easy): Render or Fly — Docker image + managed Postgres.
  - Option 2: AWS EC2 + Docker Compose + Nginx, or AWS ECS/Fargate.

Frontend Overview

- Framework: React (hooks), create with `create-react-app` or Vite.
- Pages:
  - Login
  - Dashboard (role-specific)
  - Create Request form (with file upload and inline items)
  - Requests list (filters & pagination)
  - Request detail (approval actions and history)
  - Receipt submission UI
  - Finance PO/Receipt page with validation results

Testing

- Backend:
  - Unit tests for models, approval logic, PO generation.
  - Integration tests for endpoints (DRF API tests).
  - Concurrency test simulating concurrent approvals (use threading or test DB transactions).
- Frontend:
  - Basic component tests and an end-to-end flow (Cypress or Playwright optional).
- CI: GitHub Actions to run tests and build Docker image.

Acceptance Criteria

- Staff can create a PR with optional proforma file and items.
- Approvers can approve/reject at appropriate levels; any rejection flags PR as `REJECTED`.
- After final approval, a `PurchaseOrder` record is created and a PO document generated.
- Staff can upload receipt and receive validation result against PO.
- RBAC enforced; unauthenticated access blocked.
- App runs via `docker-compose up --build` using provided `Dockerfile` and `docker-compose.yml`.
- Public deployment accessible via URL; README includes URL and setup instructions.
- API documented via Swagger or Postman collection in the repo.

Deliverables

- Django project and app code (models, serializers, views, tests).
- `Dockerfile` and `docker-compose.yml`.
- Frontend app under `frontend/` (React) with build config.
- API docs (Swagger/OpenAPI or `postman_collection.json`).
- `README.md` with setup/run instructions and public URL.
- Demo credentials / sample seed data.

Timeline (suggested to meet Nov 26 deadline)

- Day 1: Finalize SRS, scaffold Django project, Dockerfile, and basic auth.
- Day 2: Implement models, migrations, serializers, and basic endpoints (create/list/get).
- Day 3: Implement approval workflow & PO generation logic + tests.
- Day 4: Implement document upload + async processing (basic PDF parsing) and receipt validation.
- Day 5: Build React frontend (login, create request, lists, approvals).
- Day 6: Polish, add Swagger docs, Docker-compose, deploy to public host, finalize README.

Risks & Mitigations

- OCR/LLM accuracy: Mitigate by combining heuristics + allow manual editing of extracted fields.
- Deployment complexity: Use managed platforms (Render, Fly) for faster public deployment.
- Concurrency: Implement DB transactions and tests early.

Next Steps

- Implement backend scaffold (Django project, models, basic endpoints).
- Or: generate API OpenAPI spec / Postman collection from SRS to guide implementation.
- Or: begin frontend scaffolding.

---

Document version: 1.0
Last updated: 2025-11-20
