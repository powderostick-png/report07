# Agent Notes

## Project Overview

This project is a local Django + Vue application.

- Backend: Django 6.0.7
- Admin UI: django-simpleui 2026.1.13
- Frontend: Vue 3.5 + Vite 8
- Database: SQLite, stored at `db.sqlite3`
- Django project module: `config`
- Django app: `core`
- Vue app directory: `frontend`

The Django admin remains available at `/admin/`. The public frontend route `/` is handled by the built Vue app.

## Environment

Use the project virtual environment at `.venv`.

PowerShell activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
. .\.venv\Scripts\Activate.ps1
```

If using commands directly, prefer:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

## Backend Commands

Run Django checks:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Apply migrations:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Start Django development server:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Django URLs:

- Frontend through Django: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

## Frontend Commands

The Vue app lives in `frontend/`.

Start Vite dev server:

```powershell
cd frontend
pnpm dev
```

Build Vue assets for Django:

```powershell
cd frontend
pnpm build
```

The production build outputs to:

```text
static/frontend/
```

Django serves `static/frontend/index.html` from `core.views.vue_frontend`.

## Important Files

- `config/settings.py`: Django settings, installed apps, language, timezone, static file config.
- `config/urls.py`: Routes `/admin/` to Django admin and all other non-static routes to Vue.
- `core/views.py`: Serves the built Vue `index.html`.
- `frontend/vite.config.js`: Sets Vite build output to `../static/frontend`.
- `frontend/src/App.vue`: Main Vue frontend page.
- `frontend/src/style.css`: Vue frontend styling.

## Current Configuration Notes

- `simpleui` must stay before `django.contrib.admin` in `INSTALLED_APPS`.
- Default language is Simplified Chinese: `LANGUAGE_CODE = 'zh-hans'`.
- Time zone is Shanghai: `TIME_ZONE = 'Asia/Shanghai'`.
- The Vue frontend should be rebuilt after frontend code changes when testing through Django on port `8000`.
- For hot reload during frontend development, use Vite on port `5173`.

## Admin Account

A local superuser has been created for development:

- Username: `lummo__viltrox`
- Email: `powderostick@gmail.com`

Do not store plaintext passwords in project files. Reset the password with:

```powershell
.\.venv\Scripts\python.exe manage.py changepassword lummo__viltrox
```

## Development Guidance

- Keep Django backend and Vue frontend concerns separate.
- Add Django API endpoints under `core` or a new dedicated Django app as the project grows.
- Keep `/admin/` reserved for Django admin.
- Do not edit files inside `.venv`, `frontend/node_modules`, or generated build assets unless specifically required.
- After backend changes, run `manage.py check`.
- After frontend changes, run `pnpm build` before validating through Django.
