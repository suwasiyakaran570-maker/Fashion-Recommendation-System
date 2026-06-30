"""
Generate Similarity Matrix for Fashion Recommender
===================================================
This script creates the similarity_matrix.npy and article_ids.npy files
needed by the recommender system.

Run this ONCE after setting up your project:
    python generate_similarity_matrix.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder
import sys

# Add src to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import *

print("=" * 70)
print("GENERATING SIMILARITY MATRIX FOR FASHION RECOMMENDER")
print("=" * 70)

# Step 1: Load articles data
print("\n[1/5] Loading articles data...")
try:
    articles_df = pd.read_csv(ARTICLES_CSV)
    print(f"✓ Loaded {len(articles_df):,} articles")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Step 2: Feature engineering
print("\n[2/5] Creating feature vectors...")

# Select features for similarity
feature_columns = [
    'product_type_no',
    'product_group_no',
    'graphical_appearance_no',
    'colour_group_code',
    'department_no',
    'index_group_no',
    'section_no',
    'garment_group_no'
]

# Check which columns exist
available_features = [col for col in feature_columns if col in articles_df.columns]
print(f"   Using features: {', '.join(available_features)}")

if len(available_features) == 0:
    print("✗ No numeric features found! Using categorical encoding...")
    # Fallback: encode categorical columns
    le = LabelEncoder()
    articles_df['product_type_encoded'] = le.fit_transform(articles_df['product_type_name'].fillna('Unknown'))
    articles_df['product_group_encoded'] = le.fit_transform(articles_df['product_group_name'].fillna('Unknown'))
    articles_df['section_encoded'] = le.fit_transform(articles_df['section_name'].fillna('Unknown'))
    available_features = ['product_type_encoded', 'product_group_encoded', 'section_encoded']

# Create feature matrix
features_df = articles_df[['article_id'] + available_features].copy()
features_df = features_df.fillna(0)

# Step 3: Calculate similarity (limit to top 50k articles for speed)
print("\n[3/5] Calculating cosine similarity...")
max_articles = 50000  # Limit for memory efficiency
if len(features_df) > max_articles:
    print(f"   Limiting to top {max_articles:,} most popular articles...")
    # Get popular articles based on frequency in transactions
    try:
        transactions_df = pd.read_csv(TRANSACTIONS_CSV)
        popular_articles = transactions_df['article_id'].value_counts().head(max_articles).index.tolist()
        features_df = features_df[features_df['article_id'].isin(popular_articles)]
        print(f"   Selected {len(features_df):,} articles")
    except:
        print(f"   Using first {max_articles:,} articles")
        features_df = features_df.head(max_articles)

article_ids = features_df['article_id'].values
feature_matrix = features_df[available_features].values

print(f"   Computing similarity for {len(article_ids):,} articles...")
print(f"   Feature matrix shape: {feature_matrix.shape}")

# Compute cosine similarity
similarity_matrix = cosine_similarity(feature_matrix)
print(f"✓ Similarity matrix shape: {similarity_matrix.shape}")

# Step 4: Save to disk
print("\n[4/5] Saving similarity matrix...")
models_dir = BASE_DIR / 'models'
models_dir.mkdir(exist_ok=True)

np.save(models_dir / 'similarity_matrix.npy', similarity_matrix)
np.save(models_dir / 'article_ids.npy', article_ids)

print(f"✓ Saved to {models_dir}/")
print(f"   - similarity_matrix.npy ({similarity_matrix.nbytes / 1024 / 1024:.1f} MB)")
print(f"   - article_ids.npy ({article_ids.nbytes / 1024:.1f} KB)")

# Step 5: Test loading
print("\n[5/5] Testing load...")
test_sim = np.load(models_dir / 'similarity_matrix.npy')
test_ids = np.load(models_dir / 'article_ids.npy')
print(f"✓ Successfully loaded {len(test_ids):,} article similarities")

print("\n" + "=" * 70)
print("✓ SIMILARITY MATRIX GENERATION COMPLETE!")
print("=" * 70)
print("\nYou can now run your Flask app:")
print("    python run.py")
print("\nThe recommender will use similarity-based recommendations!")