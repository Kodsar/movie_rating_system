# Movie Rating System

A REST API for managing a movie catalog and submitting ratings, built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**.

This project demonstrates layered backend architecture, relational data modeling, request validation, database transactions, and containerized development.

## Features

- Create, retrieve, update, and delete movies.
- Browse movies with pagination.
- Filter movies by title, release year, and genre.
- Submit ratings with scores from 1 to 10.
- Retrieve director information, genres, average ratings, and rating counts.
- Validate request bodies and query parameters.
- Validate director and genre references before saving movies.
- Handle database transactions with commit and rollback.
- Log HTTP requests and service operations.
- Manage database schema changes with Alembic.
- Run the API and database using Docker Compose.

## Technology Stack

| Component | Technology |
| --- | --- |
| Language | Python 3.12+ |
| API framework | FastAPI |
| Application server | Uvicorn |
| Validation | Pydantic 2 |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2 |
| Database migrations | Alembic |
| Database driver | psycopg2 |
| Containerization | Docker and Docker Compose |
| Container dependency installation | uv |

## Architecture

The application separates HTTP handling, business logic, and database access.

| Directory | Responsibility |
| --- | --- |
| `app/controller/` | API endpoints and response helpers |
| `app/schemas/` | Request validation and response schemas |
| `app/services/` | Business rules and transaction management |
| `app/repositories/` | Database queries and persistence operations |
| `app/models/` | SQLAlchemy data models |
| `app/db/` | Database configuration and sessions |
| `app/core/` | Shared configuration and logging |
| `app/middleware/` | Request logging middleware |
| `alembic/` | Versioned database migrations |
| `scripts/` | Seed data, SQL scripts, and seed verification |

Database sessions are injected into routes through FastAPI dependencies. Controllers delegate business operations to services, which use repositories to access the database.

## Database Model

The initial migration creates five tables:

- `directors`: director information.
- `genres`: available movie genres.
- `movies`: movie information and director references.
- `genres_movie`: many-to-many relationships between movies and genres.
- `movie_ratings`: individual movie ratings.

Movie list and detail responses include the average rating and number of ratings. Movies without ratings return a null average and a zero rating count.

## Getting Started

### Prerequisites

- Git
- Docker and Docker Compose
- Python 3.12+ for local API development

### Clone the Repository

```bash
git clone https://github.com/Kodsar/movie_rating_system.git
cd movie_rating_system
cp .env.example .env
```

## Run with Docker Compose

### 1. Configure Environment Variables

Set the following connection string in `.env` for the API running inside Docker:

```dotenv
DATABASE_URL=postgresql+psycopg2://movieuser:moviepass@db:5432/moviedb
```

These development credentials match `docker-compose.yml`. Inside the Compose network, PostgreSQL is available through the hostname `db`.

### 2. Start PostgreSQL

```bash
docker compose up -d db
docker compose exec db pg_isready -U movieuser -d moviedb
```

Wait until PostgreSQL reports that it is accepting connections.

### 3. Build and Start the API

```bash
docker compose up --build api
```

The API startup command applies migrations with `alembic upgrade head` before starting Uvicorn.

The current Compose configuration uses dependency ordering without a database readiness health check. Starting PostgreSQL first avoids an initial connection race.

### Service Addresses

| Service | Address |
| --- | --- |
| API | http://localhost:8002 |
| Swagger UI | http://localhost:8002/docs |
| ReDoc | http://localhost:8002/redoc |
| Health endpoint | http://localhost:8002/health |
| PostgreSQL from the host | `localhost:5435` |

### Stop the Application

```bash
docker compose down
```

Database data remains in the configured Docker volume.

## Run the API Locally

You can run PostgreSQL in Docker and the API directly on your machine.

```bash
docker compose up -d db

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install uv
uv pip compile pyproject.toml -o requirements.local.txt
python -m pip install -r requirements.local.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Configure `.env` to use PostgreSQL's published host port:

```dotenv
DATABASE_URL=postgresql+psycopg2://movieuser:moviepass@localhost:5435/moviedb
```

Apply migrations and start the development server:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Swagger UI is available at http://localhost:8000/docs.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/health` | Application health status |
| POST | `/api/v1/movies/` | Create a movie |
| GET | `/api/v1/movies/` | List and filter movies |
| GET | `/api/v1/movies/{movie_id}` | Retrieve movie details |
| PUT | `/api/v1/movies/{movie_id}` | Update a movie |
| DELETE | `/api/v1/movies/{movie_id}` | Delete a movie |
| POST | `/api/v1/movies/{movie_id}/ratings` | Submit a movie rating |

### Pagination and Filtering

The movie list endpoint accepts:

| Parameter | Default | Description |
| --- | --- | --- |
| `page` | `1` | Page number, starting from 1 |
| `page_size` | `10` | Results per page, from 1 to 100 |
| `title` | Unset | Case-insensitive partial title match |
| `release_year` | Unset | Filter by release year |
| `genre` | Unset | Filter by exact genre name |

Example:

```bash
curl -G 'http://localhost:8002/api/v1/movies/' \
  --data-urlencode 'page=1' \
  --data-urlencode 'page_size=10' \
  --data-urlencode 'title=matrix'
```

### Create a Movie

Example request body:

```json
{
  "title": "Example Movie",
  "director_id": 1,
  "release_year": 2025,
  "cast": "Example Actor",
  "genres": []
}
```

Use an existing director ID and existing genre IDs. An empty genre list is supported.

Validation rules include:

- Title: 1–300 characters.
- Director ID: a positive integer referencing an existing director.
- Release year: between 1800 and 2100.
- Cast: optional, with a maximum length of 1,000 characters.
- Genres: a list of existing genre IDs.

The `PUT` endpoint requires the title, director ID, and release year; it is not a partial-update endpoint.

### Submit a Rating

Replace `1` with an existing movie ID:

```bash
curl -X POST 'http://localhost:8002/api/v1/movies/1/ratings' \
  -H 'Content-Type: application/json' \
  -d '{"score": 8}'
```

Ratings must be integers between 1 and 10.

## Initial Data

Alembic migrations create the database schema but do not populate it.

Movie creation requires an existing director. To create a sample director:

```bash
docker compose exec db psql -U movieuser -d moviedb \
  -c "INSERT INTO directors (name) VALUES ('Demo Director') RETURNING id;"
```

Use the returned ID as `director_id` in your movie request.

The `scripts/` directory also includes:

- `seeddb.sql`
- TMDB movie and credits CSV files
- `seed_check.py`

Review the SQL import paths and database configuration before loading seed data.

The verification script contains a placeholder `DATABASE_URL` that must be configured before execution. It checks for 1,000 movies and more than 1,000 directors.

## Manual API Checks

Check application health:

```bash
curl http://localhost:8002/health
```

List movies:

```bash
curl 'http://localhost:8002/api/v1/movies/?page=1&page_size=10'
```

Use Swagger UI to check:

- Movie creation, retrieval, updates, and deletion.
- Rating submission.
- Invalid rating scores.
- Unknown movie IDs.
- Invalid director and genre references.
- Pagination values outside the supported range.

Missing movies return HTTP `404`. Validation failures return HTTP `422`.

## Project Scope

This software engineering course project focuses on movie catalog management and ratings.

The current implementation does not include user authentication, per-user ratings, or a recommendation engine. An automated API test suite is not currently included.
