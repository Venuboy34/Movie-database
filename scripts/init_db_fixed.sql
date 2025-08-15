-- Create Movies table
CREATE TABLE IF NOT EXISTS movie (
    id SERIAL PRIMARY KEY,
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

-- Create TVSeries table
CREATE TABLE IF NOT EXISTS tv_series (
    id SERIAL PRIMARY KEY,
    tmdb_id INTEGER UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    poster_url VARCHAR(500),
    release_date VARCHAR(20),
    language VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Season table
CREATE TABLE IF NOT EXISTS season (
    id SERIAL PRIMARY KEY,
    tv_series_id INTEGER NOT NULL,
    season_number INTEGER NOT NULL,
    FOREIGN KEY (tv_series_id) REFERENCES tv_series(id) ON DELETE CASCADE,
    UNIQUE (tv_series_id, season_number)
);

-- Create Episode table
CREATE TABLE IF NOT EXISTS episode (
    id SERIAL PRIMARY KEY,
    season_id INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    video_720p VARCHAR(500),
    FOREIGN KEY (season_id) REFERENCES season(id) ON DELETE CASCADE,
    UNIQUE (season_id, episode_number)
);
