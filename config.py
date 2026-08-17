import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smartattend-dev-secret-2024')
    
    # Environment-based database configuration (PostgreSQL with SQLite fallback)
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        pg_user = os.environ.get('POSTGRES_USER')
        pg_pass = os.environ.get('POSTGRES_PASSWORD')
        pg_host = os.environ.get('POSTGRES_HOST', 'localhost')
        pg_port = os.environ.get('POSTGRES_PORT', '5432')
        pg_db = os.environ.get('POSTGRES_DB')
        if pg_user and pg_pass and pg_db:
            db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
            
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url or 'sqlite:///smartattend.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
