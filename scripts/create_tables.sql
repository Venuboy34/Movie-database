-- Create a shared sequence for all media (movies + tv_series)
CREATE SEQUENCE IF NOT EXISTS media_id_seq START 1;

-- Movies table (uses shared sequence)
CREATE TABLE IF NOT EXISTS movie (
    id INT PRIMARY KEY DEFAULT nextval('media_id_seq'),
    tmdb_id INTEGER UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    poster_url VARCHAR(500),
    release_date VARCHAR(20),
    language VARCHAR(50),
    video_720p VARCHAR(500),
    video_1080p VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TV Series table (uses same shared sequence)
CREATE TABLE IF NOT EXISTS tv_series (
    id INT PRIMARY KEY DEFAULT nextval('media_id_seq'),
    tmdb_id INTEGER UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    poster_url VARCHAR(500),
    release_date VARCHAR(20),
    language VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seasons table (keeps its own sequence)
CREATE TABLE IF NOT EXISTS season (
    id SERIAL PRIMARY KEY,
    tv_series_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    FOREIGN KEY (tv_series_id) REFERENCES tv_series(id) ON DELETE CASCADE,
    UNIQUE (tv_series_id, season_number)
);

-- Episodes table (keeps its own sequence)
CREATE TABLE IF NOT EXISTS episode (
    id SERIAL PRIMARY KEY,
    season_id INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    video_720p VARCHAR(500),
    FOREIGN KEY (season_id) REFERENCES season(id) ON DELETE CASCADE,
    UNIQUE (season_id, episode_number)
);

-- Set the sequence to the current maximum ID + 1 (if migrating existing data)
-- (Run this only if you have existing data)
-- SELECT setval('media_id_seq', (SELECT GREATEST(MAX(id), 0) FROM movie) + 1);
-- SELECT setval('media_id_seq', (SELECT GREATEST(MAX(id), (SELECT MAX(id) FROM tv_series), 0) + 1));
