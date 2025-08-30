import os
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from functools import wraps
from datetime import datetime

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

# Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', '52f6a75a38a397d940959b336801e1c3')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'Venera')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Venera')

# TMDB Configuration
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/original'

def get_db_connection():
    """Get database connection"""
    try:
        if DATABASE_URL:
            # Fix for psycopg2 compatibility
            db_url = DATABASE_URL
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        else:
            # Fallback for local development
            conn = psycopg2.connect(
                "host=localhost dbname=media_db user=postgres password=password",
                cursor_factory=RealDictCursor
            )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create single media table with JSONB fields
        cursor.execute('''
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
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_type ON media(type);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_tmdb_id ON media(tmdb_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_title ON media USING gin(to_tsvector(\'english\', title));')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully")
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        if conn:
            conn.close()
        return False

# Authentication decorator
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != ADMIN_USERNAME or auth.password != ADMIN_PASSWORD:
            response = jsonify({'error': 'Authentication required'})
            response.status_code = 401
            response.headers['WWW-Authenticate'] = 'Basic realm="Admin Panel"'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        return f(*args, **kwargs)
    return decorated_function

# CORS response helper
def make_cors_response(data, status_code=200):
    response = app.response_class(
        response=json.dumps(data, indent=4, ensure_ascii=False) if isinstance(data, (dict, list)) else data,
        status=status_code,
        mimetype='application/json'
    )
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
    return response

# TMDB API Functions
def fetch_tmdb_movie(tmdb_id):
    """Fetch movie details from TMDB with cast"""
    try:
        print(f"Fetching movie details for TMDB ID: {tmdb_id}")
        url = f"{TMDB_BASE_URL}/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Fetch cast details
            cast_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/credits?api_key={TMDB_API_KEY}"
            cast_response = requests.get(cast_url, timeout=10)
            cast_data = []
            
            if cast_response.status_code == 200:
                cast_info = cast_response.json().get('cast', [])[:10]  # Limit to 10 main cast
                for person in cast_info:
                    cast_data.append({
                        'name': person.get('name', ''),
                        'character': person.get('character', ''),
                        'image': f"{TMDB_IMAGE_BASE_URL}{person.get('profile_path')}" if person.get('profile_path') else None
                    })
            
            return {
                'title': data.get('title', ''),
                'description': data.get('overview', ''),
                'thumbnail': f"{TMDB_IMAGE_BASE_URL}{data.get('poster_path')}" if data.get('poster_path') else '',
                'release_date': data.get('release_date', ''),
                'language': data.get('original_language', ''),
                'rating': round(data.get('vote_average', 0), 1),
                'cast': cast_data
            }
        else:
            print(f"TMDB API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching TMDB movie: {e}")
        return None

def fetch_tmdb_tv(tmdb_id):
    """Fetch TV series details from TMDB with cast"""
    try:
        print(f"Fetching TV series details for TMDB ID: {tmdb_id}")
        url = f"{TMDB_BASE_URL}/tv/{tmdb_id}?api_key={TMDB_API_KEY}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Fetch cast details
            cast_url = f"{TMDB_BASE_URL}/tv/{tmdb_id}/credits?api_key={TMDB_API_KEY}"
            cast_response = requests.get(cast_url, timeout=10)
            cast_data = []
            
            if cast_response.status_code == 200:
                cast_info = cast_response.json().get('cast', [])[:10]  # Limit to 10 main cast
                for person in cast_info:
                    cast_data.append({
                        'name': person.get('name', ''),
                        'character': person.get('character', ''),
                        'image': f"{TMDB_IMAGE_BASE_URL}{person.get('profile_path')}" if person.get('profile_path') else None
                    })
            
            return {
                'title': data.get('name', ''),
                'description': data.get('overview', ''),
                'thumbnail': f"{TMDB_IMAGE_BASE_URL}{data.get('poster_path')}" if data.get('poster_path') else '',
                'release_date': data.get('first_air_date', ''),
                'language': data.get('original_language', ''),
                'rating': round(data.get('vote_average', 0), 1),
                'cast': cast_data
            }
        else:
            print(f"TMDB API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching TMDB TV: {e}")
        return None

# Routes
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error in index route: {e}")
        return make_cors_response({
            'status': 'success',
            'message': 'Media Database Flask Application',
            'version': '3.0 - Single Media Table with JSONB',
            'cors_enabled': True,
            'endpoints': {
                'admin_panel': '/admin',
                'public_api': '/media',
                'search': '/media?q=query',
                'health': '/health',
                'api_docs': '/api/docs'
            }
        })

@app.route('/admin')
@auth_required
def admin_panel():
    try:
        return render_template('admin.html')
    except Exception as e:
        print(f"Error in admin route: {e}")
        return make_cors_response({'error': 'Could not load admin panel', 'details': str(e)}, 500)

# TMDB Proxy Routes
@app.route('/api/tmdb/movie/<int:tmdb_id>')
@auth_required
def get_tmdb_movie(tmdb_id):
    try:
        details = fetch_tmdb_movie(tmdb_id)
        if details:
            return make_cors_response({
                'status': 'success',
                'message': f'Movie "{details["title"]}" loaded successfully',
                'data': details
            })
        return make_cors_response({
            'status': 'error', 
            'message': f'Movie with TMDB ID {tmdb_id} not found'
        }, 404)
    except Exception as e:
        print(f"Error in TMDB movie API: {e}")
        return make_cors_response({
            'status': 'error',
            'message': 'Failed to load movie details'
        }, 500)

@app.route('/api/tmdb/tv/<int:tmdb_id>')
@auth_required
def get_tmdb_tv(tmdb_id):
    try:
        details = fetch_tmdb_tv(tmdb_id)
        if details:
            return make_cors_response({
                'status': 'success',
                'message': f'TV series "{details["title"]}" loaded successfully',
                'data': details
            })
        return make_cors_response({
            'status': 'error',
            'message': f'TV series with TMDB ID {tmdb_id} not found'
        }, 404)
    except Exception as e:
        print(f"Error in TMDB TV API: {e}")
        return make_cors_response({
            'status': 'error',
            'message': 'Failed to load TV series details'
        }, 500)

# Admin API Routes
@app.route('/admin/media', methods=['POST'])
@auth_required
def create_media():
    try:
        data = request.get_json()
        if not data:
            return make_cors_response({'error': 'No data provided'}), 400

        conn = get_db_connection()
        if not conn:
            return make_cors_response({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        
        # Insert into single media table
        cursor.execute('''
            INSERT INTO media (type, tmdb_id, title, description, thumbnail, release_date, 
                             language, rating, cast, video_links, download_links, seasons)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (
            data['type'],
            data.get('tmdb_id'),
            data['title'],
            data.get('description', ''),
            data.get('thumbnail', ''),
            data.get('release_date', ''),
            data.get('language', ''),
            data.get('rating'),
            json.dumps(data.get('cast', [])),
            json.dumps(data.get('video_links', {})),
            json.dumps(data.get('download_links', {})),
            json.dumps(data.get('seasons', {}))
        ))
        
        media_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        
        return make_cors_response({
            'status': 'success',
            'message': f'{data["type"].title()} "{data["title"]}" added successfully',
            'id': media_id
        })
    except Exception as e:
        print(f"Error adding media: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return make_cors_response({
            'status': 'error',
            'message': 'Failed to add media'
        }, 500)

@app.route('/admin/media/<int:media_id>', methods=['PUT'])
@auth_required
def update_media(media_id):
    try:
        data = request.get_json()
        conn = get_db_connection()
        if not conn:
            return make_cors_response({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        
        # Update media record
        cursor.execute('''
            UPDATE media SET 
                title = %s, description = %s, thumbnail = %s, release_date = %s,
                language = %s, rating = %s, cast = %s, video_links = %s, 
                download_links = %s, seasons = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING title
        ''', (
            data.get('title'),
            data.get('description', ''),
            data.get('thumbnail', ''),
            data.get('release_date', ''),
            data.get('language', ''),
            data.get('rating'),
            json.dumps(data.get('cast', [])),
            json.dumps(data.get('video_links', {})),
            json.dumps(data.get('download_links', {})),
            json.dumps(data.get('seasons', {})),
            media_id
        ))
        
        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            return make_cors_response({'error': 'Media not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return make_cors_response({
            'status': 'success',
            'message': f'Media "{result["title"]}" updated successfully'
        })
    except Exception as e:
        print(f"Error updating media: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return make_cors_response({
            'status': 'error',
            'message': 'Failed to update media'
        }, 500)

@app.route('/admin/media/<int:media_id>', methods=['DELETE'])
@auth_required
def delete_media(media_id):
    try:
        conn = get_db_connection()
        if not conn:
            return make_cors_response({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        
        # Get media details before deletion
        cursor.execute('SELECT title, type FROM media WHERE id = %s', (media_id,))
        media = cursor.fetchone()
        
        if not media:
            cursor.close()
            conn.close()
            return make_cors_response({'error': 'Media not found'}), 404
        
        # Delete media
        cursor.execute('DELETE FROM media WHERE id = %s', (media_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return make_cors_response({
            'status': 'success',
            'message': f'{media["type"].title()} "{media["title"]}" deleted successfully'
        })
    except Exception as e:
        print(f"Error deleting media: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return make_cors_response({
            'status': 'error',
            'message': 'Failed to delete media'
        }, 500)

@app.route('/admin/media/<int:media_id>/episodes', methods=['POST'])
@auth_required
def add_episode(media_id):
    try:
        data = request.get_json()
        conn = get_db_connection()
        if not conn:
            return make_cors_response({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        
        # Get current seasons data
        cursor.execute('SELECT seasons, title FROM media WHERE id = %s AND type = %s', (media_id, 'tv'))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conn.close()
            return make_cors_response({'error': 'TV series not found'}), 404
        
        seasons = result['seasons'] or {}
        season_key = f"season_{data['season_number']}"
        
        # Initialize season if it doesn't exist
        if season_key not in seasons:
            seasons[season_key] = {
                'season_number': data['season_number'],
                'total_episodes': 0,
                'episodes': []
            }
        
        # Check if episode already exists
        existing_episodes = [ep for ep in seasons[season_key]['episodes'] if ep['episode_number'] == data['episode_number']]
        if existing_episodes:
            cursor.close()
            conn.close()
            return make_cors_response({
                'status': 'error',
                'message': f'Episode S{data["season_number"]}E{data["episode_number"]} already exists'
            }, 400)
        
        # Add new episode
        new_episode = {
            'episode_number': data['episode_number'],
            'episode_name': data.get('episode_name', f'Episode {data["episode_number"]}'),
            'video_720p': data.get('video_720p', ''),
            'download_720p': {
                'url': data.get('download_720p', ''),
                'file_type': data.get('file_type', 'webrip')
            }
        }
        
        seasons[season_key]['episodes'].append(new_episode)
        seasons[season_key]['total_episodes'] = len(seasons[season_key]['episodes'])
        
        # Update database
        cursor.execute('''
            UPDATE media SET seasons = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE id = %s
        ''', (json.dumps(seasons), media_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return make_cors_response({
            'status': 'success',
            'message': f'Episode S{data["season_number"]}E{data["episode_number"]} added successfully'
        })
    except Exception as e:
        print(f"Error adding episode: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return make_cors_response({
            'status': 'error',
            'message': 'Failed to add episode'
        }, 500)

# Public API Routes
@app.route('/media')
def get_all_media():
    try:
        # Get search parameters
        search_query = request.args.get('q', '').strip()
        media_type = request.args.get('type', '').strip()
        
        conn = get_db_connection()
        if not conn:
            return make_cors_response({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        
        # Build query with filters
        query = 'SELECT * FROM media WHERE 1=1'
        params = []
        
        if media_type and media_type in ['movie', 'tv']:
            query += ' AND type = %s'
            params.append(media_type)
        
        if search_query:
            query += ' AND (title ILIKE %s OR description ILIKE %s)'
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        media_list = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Format response data
        formatted_media = []
        for media in media_list:
            media_data = {
                'id': media['id'],
                'type': media['type'],
                'title': media['title'],
                'description': media['description'],
                'thumbnail': media['thumbnail'],
                'release_date': media['release_date'],
                'language': media['language'],
                'rating': float(media['rating']) if media['rating'] else None,
                'cast': media['cast'] or [],
                'created_at': media['created_at'].isoformat() if media['created_at'] else None
            }
            
            if media['type'] == 'movie':
                media_data['video_links'] = media['video_links'] or {}
                media_data['download_links'] = media['download_links'] or {}
            else:  # TV series
                media_data['seasons'] = media['seasons'] or {}
                # Calculate total seasons
                seasons_data = media['seasons'] or {}
                media_data['total_seasons'] = len(seasons_data)
            
            formatted_media.append(media_data)
        
        return make_cors_response({
            'status': 'success',
            'total_count': len(formatted_media),
            'data': formatted_media
        })
    except Exception as e:
        print(f"Error loading media: {e}")
        return make_cors_response({'error': 'Failed to retrieve media'}), 500

@app.route('/media/<int:media_id>')
def get_media_details(media_id):
    try:
        conn = get_db_connection()
        if not conn:
            return make_cors_response({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        cursor.execute('SELECT * FROM media WHERE id = %s', (media_id,))
        media = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not media:
            return make_cors_response({'error': 'Media not found'}), 404
        
        # Format response based on media type
        media_data = {
            'id': media['id'],
            'type': media['type'],
            'title': media['title'],
            'description': media['description'],
            'thumbnail': media['thumbnail'],
            'release_date': media['release_date'],
            'language': media['language'],
            'rating': float(media['rating']) if media['rating'] else None,
            'cast': media['cast'] or [],
            'created_at': media['created_at'].isoformat() if media['created_at'] else None
        }
        
        if media['type'] == 'movie':
            media_data['video_links'] = media['video_links'] or {}
            media_data['download_links'] = media['download_links'] or {}
        else:  # TV series
            media_data['seasons'] = media['seasons'] or {}
            seasons_data = media['seasons'] or {}
            media_data['total_seasons'] = len(seasons_data)
        
        return make_cors_response({
            'status': 'success',
            'data': media_data
        })
    except Exception as e:
        print(f"Error loading media details: {e}")
        return make_cors_response({'error': 'Failed to retrieve media details'}), 500

@app.route('/admin/search')
@auth_required
def admin_search():
    try:
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')  # all, id, title
        
        if not query:
            return make_cors_response({'error': 'Search query is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return make_cors_response({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        
        if search_type == 'id':
            # Search by ID (media ID or TMDB ID)
            if query.isdigit():
                cursor.execute('''
                    SELECT * FROM media 
                    WHERE id = %s OR tmdb_id = %s 
                    ORDER BY created_at DESC
                ''', (int(query), int(query)))
            else:
                return make_cors_response({'error': 'ID search requires numeric input'}), 400
        else:
            # Search by title and description
            cursor.execute('''
                SELECT * FROM media 
                WHERE title ILIKE %s OR description ILIKE %s 
                ORDER BY created_at DESC
            ''', (f'%{query}%', f'%{query}%'))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return make_cors_response({
            'status': 'success',
            'query': query,
            'search_type': search_type,
            'total_results': len(results),
            'results': [dict(row) for row in results]
        })
    except Exception as e:
        print(f"Error in admin search: {e}")
        return make_cors_response({'error': 'Search failed'}), 500

@app.route('/health')
def health_check():
    try:
        conn = get_db_connection()
        if not conn:
            return make_cors_response({
                'status': 'unhealthy',
                'database': 'disconnected',
                'timestamp': datetime.utcnow().isoformat()
            }, 500)
        
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
        
        return make_cors_response({
            'status': 'healthy',
            'database': 'connected',
            'cors_enabled': True,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '3.0 - Single Media Table with JSONB'
        })
    except Exception as e:
        return make_cors_response({
            'status': 'unhealthy',
            'database': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }, 500)

@app.route('/api/stats')
def get_stats():
    try:
        conn = get_db_connection()
        if not conn:
            return make_cors_response({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        
        # Get counts by type
        cursor.execute("SELECT type, COUNT(*) as count FROM media GROUP BY type")
        type_counts = cursor.fetchall()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM media")
        total_count = cursor.fetchone()['total']
        
        # Get episode count (from seasons JSONB)
        cursor.execute('''
            SELECT SUM(
                (SELECT SUM((season_data->>'total_episodes')::int)
                 FROM jsonb_each(seasons) AS season_data
                 WHERE season_data IS NOT NULL)
            ) as total_episodes
            FROM media 
            WHERE type = 'tv' AND seasons IS NOT NULL
        ''')
        episodes_result = cursor.fetchone()
        total_episodes = episodes_result['total_episodes'] or 0
        
        cursor.close()
        conn.close()
        
        # Format statistics
        stats = {
            'status': 'success',
            'total_media': total_count,
            'total_episodes': total_episodes,
            'by_type': {row['type']: row['count'] for row in type_counts},
            'database_type': 'PostgreSQL (Neon)',
            'version': '3.0 - Single Media Table with JSONB',
            'cors_enabled': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return make_cors_response(stats)
    except Exception as e:
        print(f"Error getting stats: {e}")
        return make_cors_response({'error': 'Failed to get stats'}), 500

@app.route('/api/docs')
def api_docs():
    try:
        return render_template('api_docs.html')
    except Exception as e:
        print(f"Error loading API docs: {e}")
        return make_cors_response({
            'message': 'Media Database API Documentation',
            'version': '3.0 - Single Media Table with JSONB',
            'cors_enabled': True,
            'public_endpoints': {
                'get_all_media': {
                    'url': '/media',
                    'method': 'GET',
                    'description': 'Get all media',
                    'query_params': ['q (search)', 'type (movie|tv)']
                },
                'get_media_detail': {
                    'url': '/media/<id>',
                    'method': 'GET',
                    'description': 'Get specific media with full details'
                },
                'health_check': {
                    'url': '/health',
                    'method': 'GET',
                    'description': 'API health check'
                },
                'get_stats': {
                    'url': '/api/stats',
                    'method': 'GET',
                    'description': 'Get database statistics'
                }
            },
            'admin_endpoints': {
                'admin_panel': '/admin',
                'tmdb_movie_proxy': '/api/tmdb/movie/<tmdb_id>',
                'tmdb_tv_proxy': '/api/tmdb/tv/<tmdb_id>',
                'create_media': 'POST /admin/media',
                'update_media': 'PUT /admin/media/<id>',
                'delete_media': 'DELETE /admin/media/<id>',
                'add_episode': 'POST /admin/media/<id>/episodes',
                'admin_search': '/admin/search?q=<query>&type=<all|id|title>'
            },
            'authentication': {
                'type': 'Basic Auth',
                'username': 'Venera',
                'password': 'Venera'
            },
                            'features': [
                'Single media table with JSONB fields',
                'Full CORS support',
                'TMDB integration with cast data',
                'Flexible episode management',
                'Search by title and description',
                'Pretty-printed JSON responses',
                'Admin authentication',
                'Health monitoring'
            ]
        })

# Error handlers with CORS support
@app.errorhandler(404)
def not_found(error):
    return make_cors_response({
        'status': 'error',
        'message': 'Endpoint not found',
        'error_code': 404
    }, 404)

@app.errorhandler(500)
def internal_error(error):
    return make_cors_response({
        'status': 'error',
        'message': 'Internal server error',
        'error_code': 500
    }, 500)

@app.errorhandler(405)
def method_not_allowed(error):
    return make_cors_response({
        'status': 'error',
        'message': 'Method not allowed',
        'error_code': 405
    }, 405)

# Handle preflight requests for CORS
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_cors_response({'message': 'CORS preflight successful'})
        return response

# Initialize database on startup
init_db()

# For Vercel deployment
if __name__ != '__main__':
    application = app
else:
    app.run(debug=True, host='0.0.0.0', port=5000)
