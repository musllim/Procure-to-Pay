# Procure-to-Pay — Mini Purchase Request & Approval System

This repository contains the backend scaffold for the IST Africa assessment (Django + DRF).

Quickstart (local):

```bash
cd /d/u/dev/Procure-to-Pay
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Or run with Docker Compose:

```bash
docker-compose up --build
```

API base: `http://localhost:8000/api/`

SRS: `docs/SRS.md`
