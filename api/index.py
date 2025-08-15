from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
import json
from functools import wraps
import os
from datetime import datetime
import traceback

app = Flask(__name__, template_folder='../templates')
app.config['SECRET_KEY'] = 'zero-creations-media-database-2024'

# Enable CORS for all routes and origins
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
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'

# Database Models - UPDATED: Removed unique constraint on tmdb_id
class Movie(db.Model):
    __tablename__ = 'movie'
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, nullable=False)  # Removed unique=True
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    poster_url = db.Column(db.String(500))
    release_date = db.Column(db.String(20))
    language = db.Column(db.String(50))
    video_720p = db.Column(db.String(500))
    video_1080p = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class TVSeries(db.Model):
    __tablename__ = 'tv_series'
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, nullable=False)  # Removed unique=True
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    poster_url = db.Column(db.String(500))
    release_date = db.Column(db.String(20))
    language = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    seasons = db.relationship('Season', backref='tv_series', lazy=True, cascade='all, delete-orphan')

class Season(db.Model):
    __tablename__ = 'season'
    id = db.Column(db.Integer, primary_key=True)
    tv_series_id = db.Column(db.Integer, db.ForeignKey('tv_series.id'), nullable=False)
    season_number = db.Column(db.Integer, nullable=False)
    episodes = db.relationship('Episode', backref='season', lazy=True, cascade='all, delete-orphan')
    __table_args__ = (db.UniqueConstraint('tv_series_id', 'season_number'),)

class Episode(db.Model):
    __tablename__ = 'episode'
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    episode_number = db.Column(db.Integer, nullable=False)
    video_720p = db.Column(db.String(500))
    __table_args__ = (db.UniqueConstraint('season_id', 'episode_number'),)

# Initialize database with error handling
def init_db():
    try:
        with app.app_context():
            db.create_all()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

# Authentication decorator
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth = request.authorization
            if not auth or auth.username != 'venura' or auth.password != 'venura':
                response = jsonify({'error': 'Authentication required'})
                response.status_code = 401
                response.headers['WWW-Authenticate'] = 'Basic realm="Admin Panel"'
                return response
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Auth error: {e}")
            return jsonify({'error': 'Authentication failed'}), 500
    return decorated_function

# TMDB API Functions with error handling
def fetch_movie_details(tmdb_id):
    try:
        url = f"{TMDB_BASE_URL}/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'title': data.get('title', ''),
                'description': data.get('overview', ''),
                'poster_url': f"{TMDB_IMAGE_BASE_URL}{data.get('poster_path', '')}" if data.get('poster_path') else '',
                'release_date': data.get('release_date', ''),
                'language': data.get('original_language', '')
            }
    except Exception as e:
        print(f"Error fetching movie details: {e}")
    return None

def fetch_tv_details(tmdb_id):
    try:
        url = f"{TMDB_BASE_URL}/tv/{tmdb_id}?api_key={TMDB_API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'title': data.get('name', ''),
                'description': data.get('overview', ''),
                'poster_url': f"{TMDB_IMAGE_BASE_URL}{data.get('poster_path', '')}" if data.get('poster_path') else '',
                'release_date': data.get('first_air_date', ''),
                'language': data.get('original_language', '')
            }
    except Exception as e:
        print(f"Error fetching TV details: {e}")
    return None

# Custom CORS response helper
def make_cors_response(data, status_code=200):
    response = app.response_class(
        response=json.dumps(data, indent=4) if isinstance(data, (dict, list)) else data,
        status=status_code,
        mimetype='application/json'
    )
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
    return response

# Add OPTIONS handler for preflight requests
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_cors_response("")
        return response

# Routes with comprehensive error handling
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error in index route: {e}")
        return make_cors_response({
            'status': 'success',
            'message': 'Zero Creations Media Database is running',
            'version': '2.0',
            'endpoints': {
                'admin_panel': '/admin',
                'public_api': '/media',
                'search': '/search?q=query',
                'health': '/health',
                'stats': '/api/stats',
                'docs': '/api/docs'
            },
            'cors_enabled': True,
            'database_connected': True
        })

@app.route('/admin')
@auth_required
def admin_panel():
    try:
        return render_template('admin_all_in_one.html')
    except Exception as e:
        print(f"Error in admin route: {e}")
        return make_cors_response({'error': 'Could not load admin panel', 'details': str(e)}, 500)

# Health check endpoint
@app.route('/health')
def health_check():
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return make_cors_response({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return make_cors_response({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500)

# TMDB API Routes
@app.route('/api/tmdb/movie/<int:tmdb_id>')
@auth_required
def get_tmdb_movie(tmdb_id):
    try:
        details = fetch_movie_details(tmdb_id)
        if details:
            return make_cors_response(details)
        return make_cors_response({'error': 'Movie not found'}, 404)
    except Exception as e:
        print(f"Error in TMDB movie API: {e}")
        return make_cors_response({'error': 'Failed to fetch movie details'}, 500)

@app.route('/api/tmdb/tv/<int:tmdb_id>')
@auth_required
def get_tmdb_tv(tmdb_id):
    try:
        details = fetch_tv_details(tmdb_id)
        if details:
            return make_cors_response(details)
        return make_cors_response({'error': 'TV series not found'}, 404)
    except Exception as e:
        print(f"Error in TMDB TV API: {e}")
        return make_cors_response({'error': 'Failed to fetch TV details'}, 500)

# FIXED: Admin API to get all media for editing
@app.route('/api/admin/media', methods=['GET'])
@auth_required
def get_admin_media():
    """Get all media for admin panel with proper error handling"""
    try:
        print("📡 Admin media request received")
        
        # Get all movies with error handling
        try:
            movies = Movie.query.all()
            print(f"📽️ Found {len(movies)} movies")
        except Exception as e:
            print(f"❌ Error fetching movies: {e}")
            movies = []
        
        # Get all TV series with error handling
        try:
            tv_series = TVSeries.query.all()
            print(f"📺 Found {len(tv_series)} TV series")
        except Exception as e:
            print(f"❌ Error fetching TV series: {e}")
            tv_series = []
        
        media_list = []
        
        # Process movies
        for movie in movies:
            try:
                media_list.append({
                    'id': movie.id,
                    'type': 'movie',
                    'title': movie.title or 'Untitled Movie',
                    'description': movie.description or '',
                    'poster_url': movie.poster_url or '',
                    'release_date': movie.release_date or '',
                    'language': movie.language or '',
                    'tmdb_id': movie.tmdb_id,
                    'video_links': {
                        '720p': movie.video_720p or '',
                        '1080p': movie.video_1080p or ''
                    },
                    'created_at': movie.created_at.isoformat() if movie.created_at else None
                })
            except Exception as e:
                print(f"❌ Error processing movie {movie.id}: {e}")
                continue
        
        # Process TV series
        for tv in tv_series:
            try:
                # Safely collect episodes
                seasons_data = {}
                total_seasons = 0
                
                try:
                    for season in tv.seasons:
                        season_key = f"season_{season.season_number}"
                        episodes_list = []
                        
                        try:
                            for episode in season.episodes:
                                episodes_list.append({
                                    'id': episode.id,
                                    'episode_number': episode.episode_number,
                                    'video_720p': episode.video_720p or ''
                                })
                        except Exception as e:
                            print(f"❌ Error processing episodes for season {season.season_number}: {e}")
                        
                        seasons_data[season_key] = {
                            'season_number': season.season_number,
                            'total_episodes': len(episodes_list),
                            'episodes': episodes_list
                        }
                        total_seasons += 1
                        
                except Exception as e:
                    print(f"❌ Error processing seasons for TV series {tv.id}: {e}")
                
                media_list.append({
                    'id': tv.id,
                    'type': 'tv',
                    'title': tv.title or 'Untitled Series',
                    'description': tv.description or '',
                    'poster_url': tv.poster_url or '',
                    'release_date': tv.release_date or '',
                    'language': tv.language or '',
                    'total_seasons': total_seasons,
                    'tmdb_id': tv.tmdb_id,
                    'seasons': seasons_data,
                    'created_at': tv.created_at.isoformat() if tv.created_at else None
                })
            except Exception as e:
                print(f"❌ Error processing TV series {tv.id}: {e}")
                continue
        
        response_data = {
            'status': 'success',
            'total_count': len(media_list),
            'movies_count': len([m for m in media_list if m['type'] == 'movie']),
            'tv_series_count': len([m for m in media_list if m['type'] == 'tv']),
            'data': media_list
        }
        
        print(f"✅ Returning {len(media_list)} media items")
        return make_cors_response(response_data)
        
    except Exception as e:
        error_details = {
            'error': 'Failed to retrieve admin media',
            'details': str(e),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }
        print(f"❌ Critical error in get_admin_media: {e}")
        print(f"📋 Traceback: {traceback.format_exc()}")
        return make_cors_response(error_details, 500)

# Admin API Routes - UPDATED: Allow duplicate movies
@app.route('/api/admin/movies', methods=['POST'])
@auth_required
def add_movie():
    try:
        data = request.get_json()
        if not data:
            return make_cors_response({'error': 'No data provided'}, 400)
        
        # REMOVED: Duplicate check - now allows same movie multiple times
        # This allows adding the same movie with different video links or other variations
        
        movie = Movie(
            tmdb_id=data['tmdb_id'],
            title=data['title'],
            description=data.get('description', ''),
            poster_url=data.get('poster_url', ''),
            release_date=data.get('release_date', ''),
            language=data.get('language', ''),
            video_720p=data['video_720p'],
            video_1080p=data['video_1080p']
        )
        
        db.session.add(movie)
        db.session.commit()
        
        # Check how many copies of this movie exist now
        movie_count = Movie.query.filter_by(tmdb_id=data['tmdb_id']).count()
        
        return make_cors_response({
            'message': 'Movie added successfully', 
            'id': movie.id,
            'duplicate_count': movie_count,
            'note': f'This is copy #{movie_count} of this movie in the database'
        })
    except Exception as e:
        print(f"Error adding movie: {e}")
        db.session.rollback()
        return make_cors_response({'error': 'Failed to add movie'}, 500)

@app.route('/api/admin/movies/<int:movie_id>', methods=['PUT'])
@auth_required
def edit_movie(movie_id):
    try:
        movie = Movie.query.get_or_404(movie_id)
        data = request.get_json()
        
        movie.title = data.get('title', movie.title)
        movie.description = data.get('description', movie.description)
        movie.poster_url = data.get('poster_url', movie.poster_url)
        movie.release_date = data.get('release_date', movie.release_date)
        movie.language = data.get('language', movie.language)
        movie.video_720p = data.get('video_720p', movie.video_720p)
        movie.video_1080p = data.get('video_1080p', movie.video_1080p)
        
        db.session.commit()
        return make_cors_response({'message': 'Movie updated successfully'})
    except Exception as e:
        print(f"Error updating movie: {e}")
        db.session.rollback()
        return make_cors_response({'error': 'Failed to update movie'}, 500)

@app.route('/api/admin/movies/<int:movie_id>', methods=['DELETE'])
@auth_required
def delete_movie(movie_id):
    try:
        movie = Movie.query.get_or_404(movie_id)
        tmdb_id = movie.tmdb_id
        db.session.delete(movie)
        db.session.commit()
        
        # Check remaining copies
        remaining_copies = Movie.query.filter_by(tmdb_id=tmdb_id).count()
        
        return make_cors_response({
            'message': 'Movie deleted successfully',
            'remaining_copies': remaining_copies,
            'note': f'{remaining_copies} copies of this movie remain in database' if remaining_copies > 0 else 'No more copies of this movie in database'
        })
    except Exception as e:
        print(f"Error deleting movie: {e}")
        db.session.rollback()
        return make_cors_response({'error': 'Failed to delete movie'}, 500)

# Admin API Routes - UPDATED: Allow duplicate TV series
@app.route('/api/admin/tv-series', methods=['POST'])
@auth_required
def add_tv_series():
    try:
        data = request.get_json()
        if not data:
            return make_cors_response({'error': 'No data provided'}, 400)
        
        # REMOVED: Duplicate check - now allows same TV series multiple times
        # This allows adding the same TV series with different configurations
        
        tv_series = TVSeries(
            tmdb_id=data['tmdb_id'],
            title=data['title'],
            description=data.get('description', ''),
            poster_url=data.get('poster_url', ''),
            release_date=data.get('release_date', ''),
            language=data.get('language', '')
        )
        
        db.session.add(tv_series)
        db.session.commit()
        
        # Check how many copies of this TV series exist now
        tv_count = TVSeries.query.filter_by(tmdb_id=data['tmdb_id']).count()
        
        return make_cors_response({
            'message': 'TV series added successfully', 
            'id': tv_series.id,
            'duplicate_count': tv_count,
            'note': f'This is copy #{tv_count} of this TV series in the database'
        })
    except Exception as e:
        print(f"Error adding TV series: {e}")
        db.session.rollback()
        return make_cors_response({'error': 'Failed to add TV series'}, 500)

@app.route('/api/admin/tv-series/<int:tv_id>', methods=['PUT'])
@auth_required
def edit_tv_series(tv_id):
    try:
        tv_series = TVSeries.query.get_or_404(tv_id)
        data = request.get_json()
        
        tv_series.title = data.get('title', tv_series.title)
        tv_series.description = data.get('description', tv_series.description)
        tv_series.poster_url = data.get('poster_url', tv_series.poster_url)
        tv_series.release_date = data.get('release_date', tv_series.release_date)
        tv_series.language = data.get('language', tv_series.language)
        
        db.session.commit()
        return make_cors_response({'message': 'TV series updated successfully'})
    except Exception as e:
        print(f"Error updating TV series: {e}")
        db.session.rollback()
        return make_cors_response({'error': 'Failed to update TV series'}, 500)

@app.route('/api/admin/tv-series/<int:tv_id>', methods=['DELETE'])
@auth_required
def delete_tv_series(tv_id):
    try:
        tv_series = TVSeries.query.get_or_404(tv_id)
        tmdb_id = tv_series.tmdb_id
        db.session.delete(tv_series)
        db.session.commit()
        
        # Check remaining copies
        remaining_copies = TVSeries.query.filter_by(tmdb_id=tmdb_id).count()
        
        return make_cors_response({
            'message': 'TV series deleted successfully',
            'remaining_copies': remaining_copies,
            'note': f'{remaining_copies} copies of this TV series remain in database' if remaining_copies > 0 else 'No more copies of this TV series in database'
        })
    except Exception as e:
        print(f"Error deleting TV series: {e}")
        db.session.rollback()
        return make_cors_response({'error': 'Failed to delete TV series'}, 500)

@app.route('/api/admin/tv-series/<int:tv_id>/episodes', methods=['POST'])
@auth_required
def add_episode(tv_id):
    try:
        data = request.get_json()
        tv_series = TVSeries.query.get_or_404(tv_id)
        
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
            return make_cors_response({'error': 'Episode already exists'}, 400)
        
        episode = Episode(
            season_id=season.id,
            episode_number=data['episode_number'],
            video_720p=data['video_720p']
        )
        
        db.session.add(episode)
        db.session.commit()
        
        return make_cors_response({'message': 'Episode added successfully'})
    except Exception as e:
        print(f"Error adding episode: {e}")
        db.session.rollback()
        return make_cors_response({'error': 'Failed to add episode'}, 500)

# NEW: Route to get all copies of a specific movie/TV series by TMDB ID
@app.route('/api/duplicates/movie/<int:tmdb_id>')
def get_movie_duplicates(tmdb_id):
    try:
        movies = Movie.query.filter_by(tmdb_id=tmdb_id).all()
        
        if not movies:
            return make_cors_response({'error': 'No movies found with this TMDB ID'}, 404)
        
        movie_list = []
        for movie in movies:
            movie_list.append({
                'id': movie.id,
                'tmdb_id': movie.tmdb_id,
                'title': movie.title,
                'description': movie.description,
                'poster_url': movie.poster_url,
                'release_date': movie.release_date,
                'language': movie.language,
                'video_links': {
                    '720p': movie.video_720p,
                    '1080p': movie.video_1080p
                },
                'created_at': movie.created_at.isoformat() if movie.created_at else None
            })
        
        return make_cors_response({
            'status': 'success',
            'tmdb_id': tmdb_id,
            'total_copies': len(movie_list),
            'movies': movie_list
        })
    except Exception as e:
        print(f"Error getting movie duplicates: {e}")
        return make_cors_response({'error': 'Failed to get movie duplicates'}, 500)

@app.route('/api/duplicates/tv/<int:tmdb_id>')
def get_tv_duplicates(tmdb_id):
    try:
        tv_series_list = TVSeries.query.filter_by(tmdb_id=tmdb_id).all()
        
        if not tv_series_list:
            return make_cors_response({'error': 'No TV series found with this TMDB ID'}, 404)
        
        series_list = []
        for tv in tv_series_list:
            # Collect all episodes with their video links
            all_episodes = {}
            for season in tv.seasons:
                season_key = f"season_{season.season_number}"
                episodes_list = []
                
                for episode in season.episodes:
                    episodes_list.append({
                        'episode_number': episode.episode_number,
                        'video_720p': episode.video_720p
                    })
                
                all_episodes[season_key] = {
                    'season_number': season.season_number,
                    'total_episodes': len(episodes_list),
                    'episodes': episodes_list
                }
            
            series_list.append({
                'id': tv.id,
                'tmdb_id': tv.tmdb_id,
                'title': tv.title,
                'description': tv.description,
                'poster_url': tv.poster_url,
                'release_date': tv.release_date,
                'language': tv.language,
                'total_seasons': len(tv.seasons),
                'seasons': all_episodes,
                'created_at': tv.created_at.isoformat() if tv.created_at else None
            })
        
        return make_cors_response({
            'status': 'success',
            'tmdb_id': tmdb_id,
            'total_copies': len(series_list),
            'tv_series': series_list
        })
    except Exception as e:
        print(f"Error getting TV duplicates: {e}")
        return make_cors_response({'error': 'Failed to get TV duplicates'}, 500)

# Public API Routes - Enhanced with all video links (unchanged)
@app.route('/media')
def get_all_media():
    try:
        movies = Movie.query.all()
        tv_series = TVSeries.query.all()
        
        media_list = []
        
        for movie in movies:
            media_list.append({
                'id': movie.id,
                'type': 'movie',
                'title': movie.title,
                'description': movie.description,
                'poster_url': movie.poster_url,
                'release_date': movie.release_date,
                'language': movie.language,
                'tmdb_id': movie.tmdb_id,
                'video_links': {
                    '720p': movie.video_720p,
                    '1080p': movie.video_1080p
                },
                'created_at': movie.created_at.isoformat() if movie.created_at else None
            })
        
        for tv in tv_series:
            # Collect all episodes with their video links
            all_episodes = {}
            for season in tv.seasons:
                season_key = f"season_{season.season_number}"
                episodes_list = []
                
                for episode in season.episodes:
                    episodes_list.append({
                        'episode_number': episode.episode_number,
                        'video_720p': episode.video_720p
                    })
                
                all_episodes[season_key] = {
                    'season_number': season.season_number,
                    'total_episodes': len(episodes_list),
                    'episodes': episodes_list
                }
            
            media_list.append({
                'id': tv.id,
                'type': 'tv',
                'title': tv.title,
                'description': tv.description,
                'poster_url': tv.poster_url,
                'release_date': tv.release_date,
                'language': tv.language,
                'total_seasons': len(tv.seasons),
                'tmdb_id': tv.tmdb_id,
                'seasons': all_episodes,
                'created_at': tv.created_at.isoformat() if tv.created_at else None
            })
        
        return make_cors_response({
            'status': 'success',
            'total_count': len(media_list),
            'movies_count': len([m for m in media_list if m['type'] == 'movie']),
            'tv_series_count': len([m for m in media_list if m['type'] == 'tv']),
            'data': media_list
        })
    except Exception as e:
        print(f"Error in get_all_media: {e}")
        return make_cors_response({'error': 'Failed to retrieve media'}, 500)

@app.route('/media/<int:media_id>')
def get_media_details(media_id):
    try:
        # Try movie first
        movie = Movie.query.get(media_id)
        if movie:
            movie_data = {
                'id': movie.id,
                'type': 'movie',
                'title': movie.title,
                'description': movie.description,
                'poster_url': movie.poster_url,
                'release_date': movie.release_date,
                'language': movie.language,
                'tmdb_id': movie.tmdb_id,
                'video_links': {
                    '720p': movie.video_720p,
                    '1080p': movie.video_1080p
                },
                'created_at': movie.created_at.isoformat() if movie.created_at else None
            }
            return make_cors_response({
                'status': 'success',
                'data': movie_data
            })
        
        # Try TV series
        tv_series = TVSeries.query.get(media_id)
        if tv_series:
            seasons_data = {}
            
            for season in tv_series.seasons:
                season_key = f"season_{season.season_number}"
                episodes_list = []
                
                for episode in season.episodes:
                    episodes_list.append({
                        'episode_number': episode.episode_number,
                        'video_720p': episode.video_720p
                    })
                
                seasons_data[season_key] = {
                    'season_number': season.season_number,
                    'total_episodes': len(episodes_list),
                    'episodes': episodes_list
                }
            
            tv_data = {
                'id': tv_series.id,
                'type': 'tv',
                'title': tv_series.title,
                'description': tv_series.description,
                'poster_url': tv_series.poster_url,
                'release_date': tv_series.release_date,
                'language': tv_series.language,
                'total_seasons': len(tv_series.seasons),
                'tmdb_id': tv_series.tmdb_id,
                'seasons': seasons_data,
                'created_at': tv_series.created_at.isoformat() if tv_series.created_at else None
            }
            
            return make_cors_response({
                'status': 'success',
                'data': tv_data
            })
        
        return make_cors_response({'error': 'Media not found'}, 404)
    except Exception as e:
        print(f"Error in get_media_details: {e}")
        return make_cors_response({'error': 'Failed to retrieve media details'}, 500)

@app.route('/search')
def search_media():
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return make_cors_response({'error': 'Search query is required'}, 400)
        
        movies = Movie.query.filter(
            db.or_(
                Movie.title.contains(query),
                Movie.description.contains(query),
                Movie.language.contains(query)
            )
        ).all()
        
        tv_series = TVSeries.query.filter(
            db.or_(
                TVSeries.title.contains(query),
                TVSeries.description.contains(query),
                TVSeries.language.contains(query)
            )
        ).all()
        
        results = []
        
        for movie in movies:
            results.append({
                'id': movie.id,
                'type': 'movie',
                'title': movie.title,
                'description': movie.description,
                'poster_url': movie.poster_url,
                'release_date': movie.release_date,
                'language': movie.language,
                'tmdb_id': movie.tmdb_id,
                'video_links': {
                    '720p': movie.video_720p,
                    '1080p': movie.video_1080p
                },
                'created_at': movie.created_at.isoformat() if movie.created_at else None
            })
        
        for tv in tv_series:
            # Collect all episodes with their video links
            all_episodes = {}
            for season in tv.seasons:
                season_key = f"season_{season.season_number}"
                episodes_list = []
                
                for episode in season.episodes:
                    episodes_list.append({
                        'episode_number': episode.episode_number,
                        'video_720p': episode.video_720p
                    })
                
                all_episodes[season_key] = {
                    'season_number': season.season_number,
                    'total_episodes': len(episodes_list),
                    'episodes': episodes_list
                }
            
            results.append({
                'id': tv.id,
                'type': 'tv',
                'title': tv.title,
                'description': tv.description,
                'poster_url': tv.poster_url,
                'release_date': tv.release_date,
                'language': tv.language,
                'total_seasons': len(tv.seasons),
                'tmdb_id': tv.tmdb_id,
                'seasons': all_episodes,
                'created_at': tv.created_at.isoformat() if tv.created_at else None
            })
        
        return make_cors_response({
            'status': 'success',
            'query': query,
            'total_results': len(results),
            'movies_count': len([r for r in results if r['type'] == 'movie']),
            'tv_series_count': len([r for r in results if r['type'] == 'tv']),
            'results': results
        })
    except Exception as e:
        print(f"Error in search: {e}")
        return make_cors_response({'error': 'Failed to search media'}, 500)

# API Documentation endpoint
@app.route('/api/docs')
def api_docs():
    """API Documentation endpoint"""
    docs = {
        'title': 'Zero Creations Media Database API',
        'version': '2.0',
        'description': 'API for managing movies and TV series with TMDB integration',
        'base_url': request.url_root.rstrip('/'),
        'endpoints': {
            'public_endpoints': {
                '/media': {
                    'method': 'GET',
                    'description': 'Get all media (movies and TV series)',
                    'auth_required': False
                },
                '/media/<id>': {
                    'method': 'GET',
                    'description': 'Get specific media item by ID',
                    'auth_required': False
                },
                '/search?q=<query>': {
                    'method': 'GET',
                    'description': 'Search media by title, description, or language',
                    'auth_required': False
                },
                '/health': {
                    'method': 'GET',
                    'description': 'Health check endpoint',
                    'auth_required': False
                }
            },
            'admin_endpoints': {
                '/admin': {
                    'method': 'GET',
                    'description': 'Admin panel interface',
                    'auth_required': True
                },
                '/api/admin/media': {
                    'method': 'GET',
                    'description': 'Get all media for admin management',
                    'auth_required': True
                },
                '/api/admin/movies': {
                    'method': 'POST',
                    'description': 'Add new movie',
                    'auth_required': True
                },
                '/api/admin/movies/<id>': {
                    'methods': ['PUT', 'DELETE'],
                    'description': 'Update or delete movie',
                    'auth_required': True
                },
                '/api/admin/tv-series': {
                    'method': 'POST',
                    'description': 'Add new TV series',
                    'auth_required': True
                },
                '/api/admin/tv-series/<id>': {
                    'methods': ['PUT', 'DELETE'],
                    'description': 'Update or delete TV series',
                    'auth_required': True
                },
                '/api/admin/tv-series/<id>/episodes': {
                    'method': 'POST',
                    'description': 'Add episode to TV series',
                    'auth_required': True
                }
            },
            'tmdb_endpoints': {
                '/api/tmdb/movie/<tmdb_id>': {
                    'method': 'GET',
                    'description': 'Get movie details from TMDB',
                    'auth_required': True
                },
                '/api/tmdb/tv/<tmdb_id>': {
                    'method': 'GET',
                    'description': 'Get TV series details from TMDB',
                    'auth_required': True
                }
            },
            'duplicate_endpoints': {
                '/api/duplicates/movie/<tmdb_id>': {
                    'method': 'GET',
                    'description': 'Get all copies of a movie by TMDB ID',
                    'auth_required': False
                },
                '/api/duplicates/tv/<tmdb_id>': {
                    'method': 'GET',
                    'description': 'Get all copies of a TV series by TMDB ID',
                    'auth_required': False
                }
            }
        },
        'authentication': {
            'type': 'Basic Auth',
            'username': 'venura',
            'password': 'venura',
            'note': 'Required for admin and TMDB endpoints'
        },
        'features': {
            'duplicates_allowed': 'Same movie/TV series can be added multiple times',
            'cors_enabled': 'Cross-origin requests allowed',
            'tmdb_integration': 'Automatic metadata fetching from TMDB',
            'episode_management': 'Full season/episode support for TV series'
        }
    }
    
    return make_cors_response(docs)

# Stats endpoint
@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    try:
        movies_count = Movie.query.count()
        tv_series_count = TVSeries.query.count()
        seasons_count = Season.query.count()
        episodes_count = Episode.query.count()
        
        # Get unique TMDB IDs
        unique_movies = db.session.query(Movie.tmdb_id).distinct().count()
        unique_tv_series = db.session.query(TVSeries.tmdb_id).distinct().count()
        
        return make_cors_response({
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'database_stats': {
                'total_movies': movies_count,
                'total_tv_series': tv_series_count,
                'total_seasons': seasons_count,
                'total_episodes': episodes_count,
                'unique_movies': unique_movies,
                'unique_tv_series': unique_tv_series,
                'duplicate_movies': movies_count - unique_movies,
                'duplicate_tv_series': tv_series_count - unique_tv_series
            }
        })
    except Exception as e:
        print(f"Error getting stats: {e}")
        return make_cors_response({'error': 'Failed to get statistics'}, 500)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return make_cors_response({'error': 'Endpoint not found'}, 404)

@app.errorhandler(500)
def internal_error(error):
    print(f"Internal server error: {error}")
    db.session.rollback()
    return make_cors_response({'error': 'Internal server error'}, 500)

@app.errorhandler(405)
def method_not_allowed(error):
    return make_cors_response({'error': 'Method not allowed'}, 405)

# Initialize database when module loads
if __name__ == '__main__':
    init_db()
    print("🚀 Starting Flask Media Database Server...")
    print("📡 CORS enabled for all origins")
    print("🔐 Admin credentials: venura/venura")
    print("📖 API docs available at /api/docs")
    print("📊 Stats available at /api/stats")
    print("🏥 Health check at /health")
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # For production deployments (Heroku, etc.)
    init_db()
