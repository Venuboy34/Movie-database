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

-- Insert sample movies for immediate use
INSERT INTO movie (tmdb_id, title, description, poster_url, release_date, language, video_720p, video_1080p) VALUES
(550, 'Fight Club', 'An insomniac office worker and a devil-may-care soapmaker form an underground fight club that evolves into something much, much more.', 'https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg', '1999-10-15', 'en', 'https://example.com/fight_club_720p.mp4', 'https://example.com/fight_club_1080p.mp4'),
(603, 'The Matrix', 'Set in the 22nd century, The Matrix tells the story of a computer hacker who joins a group of underground insurgents fighting the vast and powerful computers who now rule the earth.', 'https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg', '1999-03-30', 'en', 'https://example.com/matrix_720p.mp4', 'https://example.com/matrix_1080p.mp4'),
(155, 'The Dark Knight', 'Batman raises the stakes in his war on crime. With the help of Lt. Jim Gordon and District Attorney Harvey Dent, Batman sets out to dismantle the remaining criminal organizations that plague the streets. The partnership proves to be effective, but they soon find themselves prey to a reign of chaos unleashed by a rising criminal mastermind known to the terrified citizens of Gotham as the Joker.', 'https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg', '2008-07-16', 'en', 'https://example.com/dark_knight_720p.mp4', 'https://example.com/dark_knight_1080p.mp4'),
(13, 'Forrest Gump', 'A man with a low IQ has accomplished great things in his life and been present during significant historic events—in each case, far exceeding what anyone imagined he could do. But despite all he has achieved, his one true love eludes him.', 'https://image.tmdb.org/t/p/w500/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg', '1994-06-23', 'en', 'https://example.com/forrest_gump_720p.mp4', 'https://example.com/forrest_gump_1080p.mp4'),
(680, 'Pulp Fiction', 'A burger-loving hit man, his philosophical partner, a drug-addled gangster''s moll and a washed-up boxer converge in this sprawling, comedic crime caper. Their adventures unfurl in three stories that ingeniously trip back and forth in time.', 'https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg', '1994-09-10', 'en', 'https://example.com/pulp_fiction_720p.mp4', 'https://example.com/pulp_fiction_1080p.mp4');

-- Insert sample TV series
INSERT INTO tv_series (tmdb_id, title, description, poster_url, release_date, language) VALUES
(1396, 'Breaking Bad', 'When Walter White, a New Mexico chemistry teacher, is diagnosed with Stage III cancer and given a prognosis of only two years left to live. He becomes filled with a sense of fearlessness and an unrelenting desire to secure his family''s financial future at any cost as he enters the dangerous world of drugs and crime.', 'https://image.tmdb.org/t/p/w500/ggFHVNu6YYI5L9pCfOacjizRGt.jpg', '2008-01-20', 'en'),
(1399, 'Game of Thrones', 'Seven noble families fight for control of the mythical land of Westeros. Friction between the houses leads to full-scale war. All while a very ancient evil awakens in the farthest north. Amidst the war, a neglected military order of misfits, the Night''s Watch, is all that stands between the realms of men and icy horrors beyond.', 'https://image.tmdb.org/t/p/w500/u3bZgnGQ9T01sWNhyveQz0wH0Hl.jpg', '2011-04-17', 'en'),
(1418, 'The Big Bang Theory', 'The sitcom is centered on five characters living in Pasadena, California: roommates Leonard Hofstadter and Sheldon Cooper; Penny, a waitress and aspiring actress who lives across the hall; and Leonard and Sheldon''s equally geeky and socially awkward friends and co-workers, mechanical engineer Howard Wolowitz and astrophysicist Raj Koothrappali. The geekiness and intellect of the four guys is contrasted for comic effect with Penny''s social skills and common sense.', 'https://image.tmdb.org/t/p/w500/ooBGRQBdbGzBxAVfExiO8r7kloA.jpg', '2007-09-24', 'en');

-- Insert sample seasons and episodes for Breaking Bad
INSERT INTO season (tv_series_id, season_number) VALUES 
(1, 1), (1, 2);

INSERT INTO episode (season_id, episode_number, video_720p) VALUES
(1, 1, 'https://example.com/breaking_bad_s01e01_720p.mp4'),
(1, 2, 'https://example.com/breaking_bad_s01e02_720p.mp4'),
(1, 3, 'https://example.com/breaking_bad_s01e03_720p.mp4'),
(2, 1, 'https://example.com/breaking_bad_s02e01_720p.mp4'),
(2, 2, 'https://example.com/breaking_bad_s02e02_720p.mp4');

-- Insert sample seasons and episodes for Game of Thrones
INSERT INTO season (tv_series_id, season_number) VALUES 
(2, 1);

INSERT INTO episode (season_id, episode_number, video_720p) VALUES
(3, 1, 'https://example.com/got_s01e01_720p.mp4'),
(3, 2, 'https://example.com/got_s01e02_720p.mp4');
