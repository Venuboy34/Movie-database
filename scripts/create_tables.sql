-- Drop old tables if migrating (uncomment if needed)
-- DROP TABLE IF EXISTS episode CASCADE;
-- DROP TABLE IF EXISTS season CASCADE;
-- DROP TABLE IF EXISTS tv_series CASCADE;
-- DROP TABLE IF EXISTS movie CASCADE;
-- DROP SEQUENCE IF EXISTS media_id_seq CASCADE;

-- Create single media table with JSONB fields
CREATE TABLE IF NOT EXISTS media (
    id SERIAL PRIMARY KEY,
    type VARCHAR(10) NOT NULL CHECK (type IN ('movie', 'tv')),
    tmdb_id INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    thumbnail VARCHAR(1000),
    release_date VARCHAR(20),
    language VARCHAR(10),
    rating DECIMAL(3,1),
    cast JSONB DEFAULT '[]'::jsonb,
    video_links JSONB DEFAULT '{}'::jsonb,
    download_links JSONB DEFAULT '{}'::jsonb,
    seasons JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_media_type ON media(type);
CREATE INDEX IF NOT EXISTS idx_media_tmdb_id ON media(tmdb_id);
CREATE INDEX IF NOT EXISTS idx_media_title ON media USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_media_created_at ON media(created_at DESC);

-- Create index for JSONB cast field (for searching actors)
CREATE INDEX IF NOT EXISTS idx_media_cast ON media USING gin(cast);

-- Create index for JSONB seasons field (for TV series)
CREATE INDEX IF NOT EXISTS idx_media_seasons ON media USING gin(seasons) WHERE type = 'tv';

-- Migration script for existing data (run only if old tables exist)
DO $$
DECLARE
    old_movie_count INTEGER;
    old_tv_count INTEGER;
    next_id INTEGER := 1;
BEGIN
    -- Check if old tables exist and have data
    SELECT COUNT(*) INTO old_movie_count FROM information_schema.tables WHERE table_name = 'movie';
    SELECT COUNT(*) INTO old_tv_count FROM information_schema.tables WHERE table_name = 'tv_series';
    
    IF old_movie_count > 0 THEN
        -- Migrate movie data if old table exists
        IF EXISTS (SELECT 1 FROM movie LIMIT 1) THEN
            INSERT INTO media (id, type, tmdb_id, title, description, thumbnail, release_date, language, rating, video_links, created_at)
            SELECT 
                id,
                'movie',
                tmdb_id,
                title,
                description,
                poster_url,
                release_date,
                language,
                NULL, -- rating not in old schema
                jsonb_build_object(
                    'video_720p', COALESCE(video_720p, ''),
                    'video_1080p', COALESCE(video_1080p, ''),
                    'video_2160p', ''
                ),
                created_at
            FROM movie
            ON CONFLICT (id) DO NOTHING;
            
            RAISE NOTICE 'Migrated % movies to new media table', (SELECT COUNT(*) FROM movie);
        END IF;
    END IF;
    
    IF old_tv_count > 0 THEN
        -- Migrate TV series data if old table exists
        IF EXISTS (SELECT 1 FROM tv_series LIMIT 1) THEN
            -- First migrate TV series basic info
            INSERT INTO media (id, type, tmdb_id, title, description, thumbnail, release_date, language, rating, seasons, created_at)
            SELECT 
                tv.id,
                'tv',
                tv.tmdb_id,
                tv.title,
                tv.description,
                tv.poster_url,
                tv.release_date,
                tv.language,
                NULL, -- rating not in old schema
                COALESCE(
                    (SELECT jsonb_object_agg(
                        'season_' || s.season_number,
                        jsonb_build_object(
                            'season_number', s.season_number,
                            'total_episodes', (SELECT COUNT(*) FROM episode WHERE season_id = s.id),
                            'episodes', COALESCE(
                                (SELECT jsonb_agg(
                                    jsonb_build_object(
                                        'episode_number', e.episode_number,
                                        'episode_name', 'Episode ' || e.episode_number,
                                        'video_720p', COALESCE(e.video_720p, ''),
                                        'download_720p', jsonb_build_object(
                                            'url', COALESCE(e.video_720p, ''),
                                            'file_type', 'webrip'
                                        )
                                    )
                                ) FROM episode e WHERE e.season_id = s.id ORDER BY e.episode_number),
                                '[]'::jsonb
                            )
                        )
                    ) FROM season s WHERE s.tv_series_id = tv.id),
                    '{}'::jsonb
                ),
                tv.created_at
            FROM tv_series tv
            ON CONFLICT (id) DO NOTHING;
            
            RAISE NOTICE 'Migrated % TV series to new media table', (SELECT COUNT(*) FROM tv_series);
        END IF;
    END IF;
    
    -- Update sequence to next available ID
    SELECT COALESCE(MAX(id), 0) + 1 INTO next_id FROM media;
    PERFORM setval('media_id_seq', next_id);
    
    RAISE NOTICE 'Database migration completed. Next ID will be: %', next_id;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Migration skipped or failed: %', SQLERRM;
END $$;

-- Sample data (remove if not needed)
-- INSERT INTO media (type, tmdb_id, title, description, thumbnail, release_date, language, rating, cast, video_links, download_links) 
-- VALUES (
--     'movie',
--     278,
--     'The Shawshank Redemption',
--     'Two imprisoned men bond over a number of years...',
--     'https://image.tmdb.org/t/p/original/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg',
--     '1994-09-23',
--     'en',
--     9.3,
--     '[{"name": "Tim Robbins", "character": "Andy Dufresne", "image": "https://image.tmdb.org/t/p/original/hsCu1JUzQQ4pl7uFxAVFJ7d9RZ6.jpg"}]'::jsonb,
--     '{"video_720p": "https://example.com/shawshank_720p.mp4", "video_1080p": "https://example.com/shawshank_1080p.mp4", "video_2160p": "https://example.com/shawshank_2160p.mp4"}'::jsonb,
--     '{"download_720p": {"url": "https://example.com/shawshank_720p.mp4", "file_type": "webrip"}, "download_1080p": {"url": "https://example.com/shawshank_1080p.mp4", "file_type": "webrip"}}'::jsonb
-- );

-- Verify table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'media' 
ORDER BY ordinal_position;
