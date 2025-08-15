# Media Database Flask Application

A full-stack Flask application for managing movies and TV series with TMDB integration, admin panel, and public API.

## 🚀 Deployment

This application is configured for deployment on Vercel with the following structure:

- `api/index.py` - Main Flask application
- `templates/` - HTML templates
- `vercel.json` - Vercel configuration
- `requirements.txt` - Python dependencies

## Features

- 🎬 Movie and TV series database
- 🔐 Admin panel with basic authentication
- 🧠 TMDB API integration for auto-filling details
- 🌐 Public JSON API with pretty printing
- 📱 Responsive web interface
- 💾 Permanent PostgreSQL database (via Neon)

## Local Development

1. Install dependencies:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

2. Run the application:
\`\`\`bash
python api/index.py
\`\`\`

3. Access the application at `http://localhost:5000`

## Admin Access

- **Username:** Venera
- **Password:** Venera

## API Endpoints

- `GET /media` - List all media
- `GET /media/<id>` - Get specific media details
- `GET /api/docs` - API documentation

## TMDB Integration

The application uses TMDB API to auto-fill movie and TV series details:
- API Key: 52f6a75a38a397d940959b336801e1c3
- Movie endpoint: https://api.themoviedb.org/3/movie/{id}
- TV endpoint: https://api.themoviedb.org/3/tv/{id}

## Database Schema

- **Movies:** TMDB ID, title, description, poster, release date, 720p/1080p links
- **TV Series:** TMDB ID, title, description, poster, release date, seasons
- **Episodes:** Season number, episode number, 720p link
- 💾 PostgreSQL database (data persists permanently via Neon)

## Vercel Deployment

The application is configured for serverless deployment on Vercel:

1. Push to GitHub repository
2. Connect to Vercel
3. Deploy automatically

The `vercel.json` configuration handles routing and Python runtime setup.
