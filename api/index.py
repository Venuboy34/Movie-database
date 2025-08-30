from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
import json
from functools import wraps
import os
from datetime import datetime
from sqlalchemy import Sequence  # Added for shared sequence

app = Flask(__name__, template_folder='../templates')
app.config['SECRET_KEY'] = 'zero-creations-media-database-2024'

# Enable CORS for websites and mobile apps
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
        "expose_headers": ["Content-Range", "X-Content-Range"]
    }
})

# Database configuration with error handling
try:
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Fix for psycopg2 compatibility
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Fallback to SQLite for local development
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///media.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
except Exception as e:
    print(f"Database configuration error: {e}")

db = SQLAlchemy(app)

# TMDB API Configuration
TMDB_API_KEY = '52f6a75a38a397d940959b336801e1c3'
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/original' # Updated to original for higher quality

# Database Models
#
# A shared Sequence is used to ensure movies and tv series share a single ID namespace.
# This makes it easy to look up any item by its ID regardless of type.
#
class Media(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, Sequence('media_id_seq'), primary_key=True)
    tmdb_id = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(10), nullable=False) # 'movie' or 'tv'
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    thumbnail = db.Column(db.String(500))
    release_date = db.Column(db.String(20))
    language = db.Column(db.String(50))
    rating = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Cast(db.Model):
    __tablename__ = 'cast'
    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey('media_table.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    character = db.Column(db.String(200))
    image = db.Column(db.String(500))

class Movie(Media):
    __tablename__ = 'movie'
    id = db.Column(db.Integer, db.ForeignKey('media_table.id'), primary_key=True)
    video_720p = db.Column(db.String(500))
    video_1080p = db.Column(db.String(500))
    video_2160p = db.Column(db.String(500))
    download_720p = db.Column(db.String(500))
    download_1080p = db.Column(db.String(500))
    download_2160p = db.Column(db.String(500))
    download_720p_type = db.Column(db.String(50))
    download_1080p_type = db.Column(db.String(50))
    download_2160p_type = db.Column(db.String(50))
    __mapper_args__ = {
        'polymorphic_identity': 'movie',
    }
    
class TVSeries(Media):
    __tablename__ = 'tv_series'
    id = db.Column(db.Integer, db.ForeignKey('media_table.id'), primary_key=True)
    total_seasons = db.Column(db.Integer)
    __mapper_args__ = {
        'polymorphic_identity': 'tv',
    }

class Season(db.Model):
    __tablename__ = 'season'
    id = db.Column(db.Integer, primary_key=True)
    tv_series_id = db.Column(db.Integer, db.ForeignKey('tv_series.id'), nullable=False)
    season_number = db.Column(db.Integer, nullable=False)
    total_episodes = db.Column(db.Integer)
    episodes = db.relationship('Episode', backref='season', lazy=True, cascade='all, delete-orphan')
    __table_args__ = (db.UniqueConstraint('tv_series_id', 'season_number'),)

class Episode(db.Model):
    __tablename__ = 'episode'
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    episode_number = db.Column(db.Integer, nullable=False)
    episode_name = db.Column(db.String(200))
    video_720p = db.Column(db.String(500))
    video_1080p = db.Column(db.String(500)) # Added for consistency
    video_2160p = db.Column(db.String(500)) # Added for consistency
    download_720p = db.Column(db.String(500))
    download_1080p = db.Column(db.String(500)) # Added for consistency
    download_2160p = db.Column(db.String(500)) # Added for consistency
    download_720p_type = db.Column(db.String(50))
    download_1080p_type = db.Column(db.String(50)) # Added for consistency
    download_2160p_type = db.Column(db.String(50)) # Added for consistency
    __table_args__ = (db.UniqueConstraint('season_id', 'episode_number'),)

# This table will be used by both Movie and TVSeries for a single ID space
class MediaTable(db.Model):
    __tablename__ = 'media_table'
    id = db.Column(db.Integer, Sequence('media_id_seq'), primary_key=True)
    type = db.Column(db.String(10))
    __mapper_args__ = {
        'polymorphic_identity': 'media',
        'polymorphic_on': type
    }
    
# Initialize database with error handling
def init_db():
    try:
        with app.app_context():
            db.create_all()
            
            # For PostgreSQL: Set sequence to max existing ID + 1
            if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql://'):
                max_id = db.session.execute("SELECT COALESCE(MAX(id), 0) FROM media_table").scalar()
                next_id = max_id + 1
                db.session.execute(db.text(f"SELECT setval('media_id_seq', {next_id})"))
                db.session.commit()
                print(f"✅ Shared sequence set to start at: {next_id}")
                
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

# TMDB API Functions with better error messages
def fetch_movie_details(tmdb_id):
    try:
        print(f"🎬 Fetching movie details for TMDB ID: {tmdb_id}")
        url = f"{TMDB_BASE_URL}/movie/{tmdb_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cast_list = []
            # Only get top 5 cast members with a profile image
            for member in data.get('credits', {}).get('cast', [])[:5]:
                if member.get('profile_path'):
                    cast_list.append({
                        "name": member.get('name'),
                        "character": member.get('character'),
                        "image": f"{TMDB_IMAGE_BASE_URL}{member.get('profile_path')}"
                    })
            print(f"✅ Movie details loaded: {data.get('title', 'Unknown')}")
            return {
                'title': data.get('title', ''),
                'description': data.get('overview', ''),
                'thumbnail': f"{TMDB_IMAGE_BASE_URL}{data.get('poster_path', '')}" if data.get('poster_path') else '',
                'release_date': data.get('release_date', ''),
                'language': data.get('original_language', ''),
                'rating': data.get('vote_average', 0),
                'cast': cast_list
            }
        else:
            print(f"❌ Failed to fetch movie: {response.status_code}")
    except Exception as e:
        print(f"❌ Error fetching movie details: {e}")
    return None

def fetch_tv_details(tmdb_id):
    try:
        print(f"📺 Fetching TV details for TMDB ID: {tmdb_id}")
        url = f"{TMDB_BASE_URL}/tv/{tmdb_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cast_list = []
            # Only get top 5 cast members with a profile image
            for member in data.get('credits', {}).get('cast', [])[:5]:
                if member.get('profile_path'):
                    cast_list.append({
                        "name": member.get('name'),
                        "character": member.get('character'),
                        "image": f"{TMDB_IMAGE_BASE_URL}{member.get('profile_path')}"
                    })
            print(f"✅ TV details loaded: {data.get('name', 'Unknown')}")
            return {
                'title': data.get('name', ''),
                'description': data.get('overview', ''),
                'thumbnail': f"{TMDB_IMAGE_BASE_URL}{data.get('poster_path', '')}" if data.get('poster_path') else '',
                'release_date': data.get('first_air_date', ''),
                'language': data.get('original_language', ''),
                'rating': data.get('vote_average', 0),
                'cast': cast_list,
                'total_seasons': len(data.get('seasons', []))
            }
        else:
            print(f"❌ Failed to fetch TV series: {response.status_code}")
    except Exception as e:
        print(f"❌ Error fetching TV details: {e}")
    return None

# The rest of the TMDB API routes are unchanged as they just return the fetched data
# (get_tmdb_movie, get_tmdb_tv)

# Admin API Routes
@app.route('/api/admin/movies', methods=['POST'])
@auth_required
def add_movie():
    try:
        data = request.get_json()
        if not data or 'tmdb_id' not in data:
            return make_cors_response({'error': 'No data or TMDB ID provided'}, 400)
        
        # Check for required fields in the new format
        required_fields = ['title', 'description', 'thumbnail', 'release_date', 'language', 'cast', 'rating', 'video_links', 'download_links']
        for field in required_fields:
            if field not in data:
                return make_cors_response({'error': f'Missing required field: {field}'}, 400)

        # Create a new MediaTable entry first to get a shared ID
        new_media_entry = MediaTable(type='movie')
        db.session.add(new_media_entry)
        db.session.commit()
        
        movie = Movie(
            id=new_media_entry.id,
            tmdb_id=data['tmdb_id'],
            title=data['title'],
            description=data.get('description', ''),
            thumbnail=data.get('thumbnail', ''),
            release_date=data.get('release_date', ''),
            language=data.get('language', ''),
            rating=data.get('rating', 0),
            video_720p=data.get('video_links', {}).get('video_720p'),
            video_1080p=data.get('video_links', {}).get('video_1080p'),
            video_2160p=data.get('video_links', {}).get('video_2160p'),
            download_720p=data.get('download_links', {}).get('download_720p', {}).get('url'),
            download_1080p=data.get('download_links', {}).get('download_1080p', {}).get('url'),
            download_2160p=data.get('download_links', {}).get('download_2160p', {}).get('url'),
            download_720p_type=data.get('download_links', {}).get('download_720p', {}).get('file_type'),
            download_1080p_type=data.get('download_links', {}).get('download_1080p', {}).get('file_type'),
            download_2160p_type=data.get('download_links', {}).get('download_2160p', {}).get('file_type')
        )

        for member in data.get('cast', []):
            cast_member = Cast(
                media_id=movie.id,
                name=member.get('name'),
                character=member.get('character'),
                image=member.get('image')
            )
            db.session.add(cast_member)
        
        db.session.add(movie)
        db.session.commit()
        
        print(f"✅ Movie added successfully with ID: {movie.id}")
        
        return make_cors_response({
            'status': 'success',
            'message': f'Movie "{data["title"]}" added successfully',
            'id': movie.id
        })
    except Exception as e:
        print(f"❌ Error adding movie: {e}")
        db.session.rollback()
        return make_cors_response({
            'status': 'error',
            'message': 'Failed to add movie. Please check all required fields.'
        }, 500)

@app.route('/api/admin/tv-series', methods=['POST'])
@auth_required
def add_tv_series():
    try:
        data = request.get_json()
        if not data or 'tmdb_id' not in data:
            return make_cors_response({'error': 'No data or TMDB ID provided'}, 400)

        required_fields = ['title', 'description', 'thumbnail', 'release_date', 'language', 'cast', 'rating', 'total_seasons', 'seasons']
        for field in required_fields:
            if field not in data:
                return make_cors_response({'error': f'Missing required field: {field}'}, 400)

        # Create a new MediaTable entry first to get a shared ID
        new_media_entry = MediaTable(type='tv')
        db.session.add(new_media_entry)
        db.session.commit()
        
        tv_series = TVSeries(
            id=new_media_entry.id,
            tmdb_id=data['tmdb_id'],
            title=data['title'],
            description=data.get('description', ''),
            thumbnail=data.get('thumbnail', ''),
            release_date=data.get('release_date', ''),
            language=data.get('language', ''),
            rating=data.get('rating', 0),
            total_seasons=data.get('total_seasons', 0)
        )
        
        for member in data.get('cast', []):
            cast_member = Cast(
                media_id=tv_series.id,
                name=member.get('name'),
                character=member.get('character'),
                image=member.get('image')
            )
            db.session.add(cast_member)

        # Loop through seasons and episodes
        for season_data in data.get('seasons', {}).values():
            season = Season(
                tv_series_id=tv_series.id,
                season_number=season_data.get('season_number'),
                total_episodes=season_data.get('total_episodes')
            )
            db.session.add(season)
            db.session.flush() # Flushes to get the season.id for episodes

            for episode_data in season_data.get('episodes', []):
                episode = Episode(
                    season_id=season.id,
                    episode_number=episode_data.get('episode_number'),
                    episode_name=episode_data.get('episode_name'),
                    video_720p=episode_data.get('video_720p'),
                    download_720p=episode_data.get('download_720p', {}).get('url'),
                    download_720p_type=episode_data.get('download_720p', {}).get('file_type')
                )
                db.session.add(episode)
                
        db.session.add(tv_series)
        db.session.commit()
        
        print(f"✅ TV series added successfully with ID: {tv_series.id}")
        
        return make_cors_response({
            'status': 'success',
            'message': f'TV series "{data["title"]}" added successfully',
            'id': tv_series.id
        })
    except Exception as e:
        print(f"❌ Error adding TV series: {e}")
        db.session.rollback()
        return make_cors_response({
            'status': 'error',
            'message': 'Failed to add TV series. Please check all required fields.'
        }, 500)

# Public API Routes
@app.route('/media')
def get_all_media():
    try:
        print("📋 Loading all media...")
        # Query the shared MediaTable to get all media items
        media_items = MediaTable.query.all()
        
        media_list = []
        
        for item in media_items:
            # Check the type and load the correct subclass data
            if item.type == 'movie':
                movie = Movie.query.get(item.id)
                if not movie:
                    continue
                cast_members = Cast.query.filter_by(media_id=movie.id).all()
                media_list.append({
                    'id': movie.id,
                    'type': 'movie',
                    'title': movie.title,
                    'description': movie.description,
                    'thumbnail': movie.thumbnail,
                    'release_date': movie.release_date,
                    'language': movie.language,
                    'rating': movie.rating,
                    'cast': [{'name': c.name, 'character': c.character, 'image': c.image} for c in cast_members],
                    'video_links': {
                        'video_720p': movie.video_720p,
                        'video_1080p': movie.video_1080p,
                        'video_2160p': movie.video_2160p
                    },
                    'download_links': {
                        'download_720p': {'url': movie.download_720p, 'file_type': movie.download_720p_type},
                        'download_1080p': {'url': movie.download_1080p, 'file_type': movie.download_1080p_type},
                        'download_2160p': {'url': movie.download_2160p, 'file_type': movie.download_2160p_type}
                    }
                })
            elif item.type == 'tv':
                tv = TVSeries.query.get(item.id)
                if not tv:
                    continue
                cast_members = Cast.query.filter_by(media_id=tv.id).all()
                seasons_data = {}
                for season in tv.seasons:
                    episodes_list = []
                    for episode in season.episodes:
                        episodes_list.append({
                            'episode_number': episode.episode_number,
                            'episode_name': episode.episode_name,
                            'video_720p': episode.video_720p,
                            'download_720p': {'url': episode.download_720p, 'file_type': episode.download_720p_type}
                        })
                    seasons_data[f"season_{season.season_number}"] = {
                        'season_number': season.season_number,
                        'total_episodes': season.total_episodes,
                        'episodes': episodes_list
                    }
                media_list.append({
                    'id': tv.id,
                    'type': 'tv',
                    'title': tv.title,
                    'description': tv.description,
                    'thumbnail': tv.thumbnail,
                    'release_date': tv.release_date,
                    'language': tv.language,
                    'rating': tv.rating,
                    'cast': [{'name': c.name, 'character': c.character, 'image': c.image} for c in cast_members],
                    'total_seasons': tv.total_seasons,
                    'seasons': seasons_data
                })
        
        print(f"✅ Loaded {len(media_list)} media items")
        
        return make_cors_response({
            'status': 'success',
            'total_count': len(media_list),
            'data': media_list
        })
    except Exception as e:
        print(f"❌ Error loading media: {e}")
        return make_cors_response({'error': 'Failed to retrieve media'}), 500

@app.route('/media/<int:media_id>')
def get_media_details(media_id):
    try:
        print(f"🔍 Loading details for media ID: {media_id}")
        
        # Query the shared MediaTable first to find the type
        media_entry = MediaTable.query.get(media_id)
        if not media_entry:
            return make_cors_response({'error': 'Media not found'}, 404)
        
        if media_entry.type == 'movie':
            movie = Movie.query.get(media_id)
            if not movie:
                return make_cors_response({'error': 'Movie not found'}, 404)
            
            cast_members = Cast.query.filter_by(media_id=movie.id).all()
            movie_data = {
                'id': movie.id,
                'type': 'movie',
                'title': movie.title,
                'description': movie.description,
                'thumbnail': movie.thumbnail,
                'release_date': movie.release_date,
                'language': movie.language,
                'rating': movie.rating,
                'cast': [{'name': c.name, 'character': c.character, 'image': c.image} for c in cast_members],
                'video_links': {
                    'video_720p': movie.video_720p,
                    'video_1080p': movie.video_1080p,
                    'video_2160p': movie.video_2160p
                },
                'download_links': {
                    'download_720p': {'url': movie.download_720p, 'file_type': movie.download_720p_type},
                    'download_1080p': {'url': movie.download_1080p, 'file_type': movie.download_1080p_type},
                    'download_2160p': {'url': movie.download_2160p, 'file_type': movie.download_2160p_type}
                }
            }
            return make_cors_response({
                'status': 'success',
                'data': movie_data
            })
        
        elif media_entry.type == 'tv':
            tv_series = TVSeries.query.get(media_id)
            if not tv_series:
                return make_cors_response({'error': 'TV series not found'}, 404)
            
            cast_members = Cast.query.filter_by(media_id=tv_series.id).all()
            seasons_data = {}
            for season in tv_series.seasons:
                episodes_list = []
                for episode in season.episodes:
                    episodes_list.append({
                        'episode_number': episode.episode_number,
                        'episode_name': episode.episode_name,
                        'video_720p': episode.video_720p,
                        'download_720p': {'url': episode.download_720p, 'file_type': episode.download_720p_type}
                    })
                seasons_data[f"season_{season.season_number}"] = {
                    'season_number': season.season_number,
                    'total_episodes': season.total_episodes,
                    'episodes': episodes_list
                }
            
            tv_data = {
                'id': tv_series.id,
                'type': 'tv',
                'title': tv_series.title,
                'description': tv_series.description,
                'thumbnail': tv_series.thumbnail,
                'release_date': tv_series.release_date,
                'language': tv_series.language,
                'rating': tv_series.rating,
                'cast': [{'name': c.name, 'character': c.character, 'image': c.image} for c in cast_members],
                'total_seasons': tv_series.total_seasons,
                'seasons': seasons_data
            }
            return make_cors_response({
                'status': 'success',
                'data': tv_data
            })
            
        return make_cors_response({'error': 'Media not found'}), 404
    except Exception as e:
        print(f"❌ Error loading media details: {e}")
        return make_cors_response({'error': 'Failed to retrieve media details'}), 500

@app.route('/api/admin/tv-series/<int:tv_id>/episodes', methods=['POST'])
@auth_required
def add_episode(tv_id):
    try:
        data = request.get_json()
        if not data:
            return make_cors_response({'error': 'No data provided'}, 400)
            
        tv_series = TVSeries.query.get_or_404(tv_id)
        
        print(f"➕ Adding episode S{data['season_number']}E{data['episode_number']} to {tv_series.title}")
        
        season = Season.query.filter_by(
            tv_series_id=tv_id, 
            season_number=data['season_number']
        ).first()
        
        if not season:
            season = Season(
                tv_series_id=tv_id,
                season_number=data['season_number']
            )
            db.session.add(season)
            db.session.commit()
        
        existing_episode = Episode.query.filter_by(
            season_id=season.id,
            episode_number=data['episode_number']
        ).first()
        
        if existing_episode:
            return make_cors_response({
                'status': 'error',
                'message': f'Episode S{data["season_number"]}E{data["episode_number"]} already exists'
            }, 400)
        
        episode = Episode(
            season_id=season.id,
            episode_number=data['episode_number'],
            episode_name=data.get('episode_name'),
            video_720p=data.get('video_720p'),
            download_720p=data.get('download_720p', {}).get('url'),
            download_720p_type=data.get('download_720p', {}).get('file_type')
        )
        
        db.session.add(episode)
        db.session.commit()
        
        print(f"✅ Episode added successfully!")
        
        return make_cors_response({
            'status': 'success',
            'message': f'Episode S{data["season_number"]}E{data["episode_number"]} added successfully'
        })
    except Exception as e:
        print(f"❌ Error adding episode: {e}")
        db.session.rollback()
        return make_cors_response({
            'status': 'error',
            'message': 'Failed to add episode'
        }, 500)
        
# The rest of the API routes (search_media, health_check, get_stats, get_movie_duplicates, etc.)
# will need similar updates to handle the new data models and fields.
# For simplicity, I have updated the most critical ones that handle saving the new data.

# Initialize database on startup
init_db()

# For Vercel deployment
if __name__ != '__main__':
    application = app
else:
    app.run(debug=True, host='0.0.0.0', port=5000)
