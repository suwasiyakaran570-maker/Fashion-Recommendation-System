import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data paths
DATA_DIR = BASE_DIR / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'
IMAGES_DIR = RAW_DATA_DIR / 'images'

# CSV files
ARTICLES_CSV = RAW_DATA_DIR / 'articles.csv'
CUSTOMERS_CSV = RAW_DATA_DIR / 'customers.csv'
TRANSACTIONS_CSV = RAW_DATA_DIR / 'transactions_train.csv'

# Processed data
MERGED_DATA_CSV = PROCESSED_DATA_DIR / 'merged_data.csv'
IMAGE_FEATURES_NPY = PROCESSED_DATA_DIR / 'image_features.npy'
PRODUCT_EMBEDDINGS_NPY = PROCESSED_DATA_DIR / 'product_embeddings.npy'

# Model paths
MODELS_DIR = BASE_DIR / 'models'
CNN_MODEL_PATH = MODELS_DIR / 'cnn_model.h5'
RECOMMENDER_MODEL_PATH = MODELS_DIR / 'recommender.pkl'

# App paths
APP_DIR = BASE_DIR / 'app'
STATIC_DIR = APP_DIR / 'static'
TEMPLATES_DIR = APP_DIR / 'templates'
UPLOAD_DIR = STATIC_DIR / 'uploads'

# Database
DATABASE_PATH = BASE_DIR / 'fashion_app.db'
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'

# Flask Config
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = True

# Recommendation settings
TOP_N_RECOMMENDATIONS = 50
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32

# Create directories if they don't exist
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, MODELS_DIR, 
                  STATIC_DIR, TEMPLATES_DIR, UPLOAD_DIR]:
    directory.mkdir(parents=True, exist_ok=True)