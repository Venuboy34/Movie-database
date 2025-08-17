-- Create shared sequence for all media content
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

-- Seasons table (independent sequence)
CREATE TABLE IF NOT EXISTS season (
    id SERIAL PRIMARY KEY,
    tv_series_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    FOREIGN KEY (tv_series_id) REFERENCES tv_series(id) ON DELETE CASCADE,
    UNIQUE (tv_series_id, season_number)
);

-- Episodes table (independent sequence)
CREATE TABLE IF NOT EXISTS episode (
    id SERIAL PRIMARY KEY,
    season_id INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    video_720p VARCHAR(500),
    FOREIGN KEY (season_id) REFERENCES season(id) ON DELETE CASCADE,
    UNIQUE (season_id, episode_number)
);

-- Migration script for existing data (run only if needed)
DO $$
BEGIN
    -- Only execute if movies table has data
    IF EXISTS (SELECT 1 FROM movie LIMIT 1) THEN
        -- Set sequence to max existing ID + 1
        PERFORM setval('media_id_seq', (SELECT MAX(id) FROM movie) + 1);
        
        -- Output confirmation
        RAISE NOTICE 'Migrated movie IDs, next ID will be %', currval('media_id_seq');
    END IF;
    
    -- Only execute if tv_series table has data
    IF EXISTS (SELECT 1 FROM tv_series LIMIT 1) THEN
        -- Advance sequence if tv_series has higher IDs
        PERFORM setval('media_id_seq', GREATEST(
            currval('media_id_seq'),
            (SELECT MAX(id) FROM tv_series) + 1
        ));
        
        -- Output confirmation
        RAISE NOTICE 'Migrated tv_series IDs, next ID will be %', currval('media_id_seq');
    END IF;
END $$;
