# API App

FastAPI backend for authentication, pricing rules, quote calculation, and exports.

## Configuration

Copy `.env.example` to `.env` and update the database settings before starting the backend. You can either set `DATABASE_URL` directly or provide `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, and `MYSQL_PASSWORD`.

## Main Modules

- `api`: HTTP routes
- `core`: settings, security, permissions
- `db`: MySQL session and migrations integration
- `models`: ORM models
- `schemas`: request/response DTOs
- `services`: business logic
- `repositories`: data access layer
- `templates`: quote export templates

