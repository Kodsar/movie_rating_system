-- seeddb.sql
-- DATA LOAD ONLY - Assumes schema is already created by Alembic.
-- Loads 1000 real movies from TMDB 5000 dataset into:
-- directors, genres, movies, genres_movie, movie_ratings
-- Run inside docker:
-- docker compose exec db psql -U movieuser -d moviedb -f /app/scripts/seeddb.sql

BEGIN;

------------------------------- 1. Cleanup Existing Data -----------------------------
DELETE FROM movie_ratings;
DELETE FROM genres_movie;
DELETE FROM movies;
DELETE FROM directors;
DELETE FROM genres;

-- Reset sequences (PostgreSQL default sequence names)
ALTER SEQUENCE directors_id_seq RESTART WITH 1;
ALTER SEQUENCE genres_id_seq RESTART WITH 1;
ALTER SEQUENCE movies_id_seq RESTART WITH 1;
ALTER SEQUENCE movie_ratings_id_seq RESTART WITH 1;

------------------------------- 2. Drop staging tables -----------------------------
DROP TABLE IF EXISTS tmdb_movies_raw CASCADE;
DROP TABLE IF EXISTS tmdb_credits_raw CASCADE;
DROP TABLE IF EXISTS tmdb_selected CASCADE;

------------------------------- 3. Create staging tables -----------------------------
CREATE TABLE tmdb_movies_raw (
    budget NUMERIC,
    genres TEXT,
    homepage TEXT,
    id INTEGER PRIMARY KEY,
    keywords TEXT,
    original_language TEXT,
    original_title TEXT,
    overview TEXT,
    popularity NUMERIC,
    production_companies TEXT,
    production_countries TEXT,
    release_date TEXT,
    revenue NUMERIC,
    runtime NUMERIC,
    spoken_languages TEXT,
    status TEXT,
    tagline TEXT,
    title TEXT,
    vote_average NUMERIC,
    vote_count INTEGER
);

CREATE TABLE tmdb_credits_raw (
    movie_id INTEGER,
    title TEXT,
    "cast" TEXT,
    crew TEXT
);

------------------------------- 4. Load raw data (psql-specific) -----------------------------
-- Use absolute paths inside the container
\copy tmdb_movies_raw (budget,genres,homepage,id,keywords,original_language,original_title,overview,popularity,production_companies,production_countries,release_date,revenue,runtime,spoken_languages,status,tagline,title,vote_average,vote_count) FROM '/app/scripts/tmdb_5000_movies.csv' CSV HEADER;

\copy tmdb_credits_raw (movie_id,title,"cast",crew) FROM '/app/scripts/tmdb_5000_credits.csv' CSV HEADER;


------------------------------- 5. Insert genres -----------------------------
INSERT INTO genres(name, description)
SELECT DISTINCT
       trim(g->>'name') AS name,
       'Imported from TMDB genres'
FROM tmdb_movies_raw m,
     LATERAL jsonb_array_elements(m.genres::jsonb) AS g
WHERE g->>'name' IS NOT NULL
ORDER BY 1;

------------------------------- 6. Insert directors -----------------------------
INSERT INTO directors(name, birth_year, description)
SELECT DISTINCT
       trim(c->>'name') AS name,
       NULL::INTEGER AS birth_year,
       'Imported from TMDB credits as Director' AS description
FROM tmdb_credits_raw cr,
     LATERAL jsonb_array_elements(cr.crew::jsonb) AS c
WHERE c->>'job' = 'Director'
  AND c->>'name' IS NOT NULL
ORDER BY 1;

------------------------------- 7. Select 1000 movies -----------------------------
CREATE TABLE tmdb_selected AS
WITH joined AS (
    SELECT
        m.id              AS tmdb_id,
        m.title,
        m.genres,
        m.release_date,
        m.vote_count,
        m.popularity,
        m.vote_average,
        cr."cast",
        cr.crew,
        (
            SELECT c2->>'name'
            FROM jsonb_array_elements(cr.crew::jsonb) c2
            WHERE c2->>'job' = 'Director'
              AND c2->>'name' IS NOT NULL
            LIMIT 1
        ) AS director_name
    FROM tmdb_movies_raw m
    JOIN tmdb_credits_raw cr
      ON cr.movie_id = m.id
),
filtered AS (
    SELECT *,
           row_number() OVER (
               ORDER BY
                   vote_count DESC NULLS LAST,
                   popularity DESC NULLS LAST,
                   vote_average DESC NULLS LAST,
                   tmdb_id ASC
           ) AS rn
    FROM joined
    WHERE director_name IS NOT NULL
)
SELECT
    tmdb_id,
    title,
    genres,
    release_date,
    "cast",
    crew,
    director_name
FROM filtered
WHERE rn <= 1000;

------------------------------- 8. Insert movies (matches your schema) -----------------------------
-- Your movies table: (title, director_id, release_year, cast)
INSERT INTO movies (title, director_id, release_year, "cast")
SELECT
    s.title,
    d.id AS director_id,
    COALESCE(
        NULLIF(split_part(s.release_date, '-', 1), '')::INT,
        2000
    ) AS release_year,
    (
        SELECT string_agg(cn, ', ')
        FROM (
            SELECT (c_el->>'name') AS cn
            FROM jsonb_array_elements(s."cast"::jsonb) AS c_el
            WHERE c_el->>'name' IS NOT NULL
            ORDER BY COALESCE((c_el->>'order')::INT, 999999)
            LIMIT 3
        ) AS sub
    ) AS cast_string
FROM tmdb_selected s
JOIN directors d
  ON d.name = s.director_name
ORDER BY s.tmdb_id;

------------------------------- 9. Insert genres_movie (your association table) -----------------------------
INSERT INTO genres_movie (movie_id, genre_id)
SELECT
    mv.id AS movie_id,
    g.id  AS genre_id
FROM movies mv
JOIN tmdb_selected s
      ON mv.title = s.title
     AND mv.director_id = (SELECT id FROM directors WHERE name = s.director_name LIMIT 1)
JOIN LATERAL jsonb_array_elements(s.genres::jsonb) AS gj ON TRUE
JOIN genres g
      ON g.name = gj->>'name'
GROUP BY mv.id, g.id;

------------------------------- 10. Generate fake ratings (matches your schema) -----------------------------
-- Your movie_ratings table: (movie_id, score, created_at)
INSERT INTO movie_ratings (movie_id, score, created_at)
SELECT
    m.id,
    (floor(random() * 10) + 1)::INT AS score,
    now() - (random() * interval '5 years')
FROM movies m,
LATERAL generate_series(1, (1 + floor(random() * 40))::INT) AS s(i);

COMMIT;
