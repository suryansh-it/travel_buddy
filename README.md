# Tripbozo - Travel App Discovery and Essentials Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Django](https://img.shields.io/badge/Django-5.1-green.svg)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)

Tripbozo helps travelers discover destination-ready apps, bundle them for sharing, and access essential country information (contacts, phrases, and travel utilities). The platform consists of a Django backend API and a Next.js frontend.

## Current Architecture

- Backend API: Django + DRF on Render
- Frontend: Next.js on Vercel
- Primary database: Aiven PostgreSQL
- Cache and short-lived session store: Upstash Redis
- Monitoring and uptime checks: UptimeRobot

## Key Product Features

### Traveler-facing features
- Country-specific app discovery and category browsing
- Destination essentials endpoint
- Country travel updates
- App-level traveler insights
- Personalized app list creation and retrieval
- QR-based sharing and bundle redirect flow

### Authentication and account
- Email/username login and registration with dj-rest-auth
- JWT create/refresh/verify endpoints
- Social auth entry points (Google/Facebook)
- User profile endpoint
- Origin-country preference endpoint
- Account delete endpoint

### Admin panel
- Manage countries and app categories
- Manage travel apps, screenshots, and reviews
- Manage origin assistance records
- Manage emergency contacts, local phrases, and useful tips

## Performance and Caching

Tripbozo uses Redis-first caching and TTL-based refresh behavior:

- Country page cache TTL: 1 hour
- App list cache TTL: 15 minutes
- Essentials cache TTL: 2 hours
- Personalized list session TTL: 24 hours

Caching is resilient by design:
- Safe cache wrappers are used for get/set operations
- If a cache read misses or fails, data is rebuilt from sources and cached again
- If Redis is temporarily unavailable, endpoints still attempt to serve fallback data

## API Overview (Current)

### Root and health
- `GET /healthz/`
- `GET /admin/`

### Homepage
- `GET /api/homepage/`
- `GET /api/homepage/search/`

### Country
- `GET /api/country/{country_code}/`
- `GET /api/country/{country_code}/categories/`
- `GET /api/country/{country_code}/apps/`
- `GET /api/country/{country_code}/essentials/`
- `GET /api/country/{country_code}/travel-updates/`
- `GET /api/country/{country_code}/apps/{app_id}/insights/`

### Personalized list and sharing
- `POST /api/personalized-list/init-session/`
- `GET|POST /api/personalized-list/`
- `GET /api/personalized-list/{session_id}/`
- `GET /api/personalized-list/qr/{session_id}/`
- `GET /api/personalized-list/download-qr/{session_id}/`
- `GET /api/personalized-list/download-text/{session_id}/`
- `GET /api/personalized-list/embed/{session_id}/`
- `GET /api/personalized-list/bundle/{session_id}/`
- `GET /api/personalized-list/bundle-redirect/{session_id}/`
- `GET /api/personalized-list/bundle-urls/{session_id}/`

### Auth
- `POST /api/auth/jwt/create/`
- `POST /api/auth/jwt/refresh/`
- `POST /api/auth/jwt/verify/`
- `GET /api/auth/user/`
- `DELETE /api/auth/user/delete/`
- `GET|PATCH /api/auth/user/origin-country/`
- `POST /api/auth/social/google/`
- `POST /api/auth/social/facebook/`
- Standard dj-rest-auth routes under `/api/auth/`

### Itinerary
- `GET /api/itinerary/{itinerary_id}/leg-suggestions/`

## Environment Variables (Backend)

Tripbozo backend reads environment variables from `backend/django_admin/env` in local development.

Required baseline values:

```env
SECRET_KEY=your_secret_key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost,127.0.0.1

DATABASE_URL=postgres://user:password@host:port/dbname?sslmode=require

REDIS_URL=redis://default:token@your-upstash-host:6379
REDIS_URL_PERSONAL_LISTS=redis://default:token@your-upstash-host:6379
REDIS_URL_ONE=redis://default:token@your-upstash-host:6379

FRONTEND_URL=https://tripbozo.com
```

Notes:
- Upstash usually uses a single logical database per instance, so multiple Redis URLs can point to the same host.
- Keep all secrets out of Git history (`backend/.gitignore` already ignores `django_admin/env`).

## Local Setup (Backend)

```bash
git clone https://github.com/suryansh-it/travel_buddy.git
cd travel_buddy/backend/django_admin

python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate # macOS/Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Optional operational commands:

```bash
python manage.py refresh_all_caches
python manage.py refresh_travel_updates
python manage.py refresh_traveler_insights
python manage.py clean_expired_sessions
```

## Deployment Model

- Backend deploys from this repo to Render
- Frontend deploys from frontend repo to Vercel
- PostgreSQL is hosted on Aiven with SSL
- Redis cache/session store is hosted on Upstash
- UptimeRobot pings backend endpoints to monitor uptime and reduce cold-start impact

## Repository Layout

```text
travel_buddy-main/
  backend/
    django_admin/
      auth_app/
      country/
      healthz/
      homepage/
      itinerary/
      personalized_list/
      services/
      django_admin/
      manage.py
      requirements.txt
  README.md
  LICENSE
```

## Related Repositories

- Frontend: https://github.com/suryansh-it/tripbozofrontend

## License

MIT License. See [LICENSE](LICENSE).
