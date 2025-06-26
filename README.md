
# TripBozo Backend


## Overview

The TripBozo Backend is a Django + Django REST Framework application responsible for:

- Generating and managing curated app bundles per country.
- Handling user sessions in Redis with 24-hour expiry.
- Serving a fully documented RESTful API (OpenAPI/Swagger).
- Processing shareable QR codes via Celery background tasks.
- Recording usage events for analytics.

---

## Key Components

| Module                    | Purpose                                                |
| ------------------------- | ------------------------------------------------------ |
| `apps.recommendation`     | Core logic for fetching and ranking travel apps        |
| `apps.sessions`           | Redis-backed session store with UUID session IDs       |
| `apps.qr`                 | Celery tasks for QR code generation                    |
| `apps.analytics`          | Event tracking & aggregation for dashboard metrics     |
| `apps.users`              | JWT-based authentication & authorization               |

---

## API Endpoints

| Method | Path                          | Description                         |
| ------ | ----------------------------- | ----------------------------------- |
| GET    | `/api/countries/`             | List supported countries            |
| GET    | `/api/bundles/?country=IN`    | Fetch curated app bundle            |
| POST   | `/api/bundles/`               | Create new bundle (returns session) |
| GET    | `/api/bundles/{id}/qr/`       | Retrieve QR code image              |
| POST   | `/api/auth/login/`            | Obtain JWT tokens                   |
| GET    | `/api/analytics/usage/`       | Fetch usage statistics              |

Full documentation: [Swagger UI](http://localhost:8000/api/docs/)

---

## Installation

```bash
git clone https://github.com/suryansh-it/travel_buddy.git
cd travel_buddy

# Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Environment variables
cp .env.example .env
