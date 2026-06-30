#!/usr/bin/env python
"""
Smart Image Feature Extraction - Only Popular Items
Extracts features from most-viewed/purchased items only
CPU-friendly, completes in 10-15 minutes
"""

import sys
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import *
from src.data_loader import DataLoader
from src.image_model import ImageFeatureExtractor

def extract_smart():
    print("\n" + "="*60)
    print("Smart Image Feature Extraction")
    print("CPU-Friendly - Only Popular Items")
    print("="*60 + "\n")

    loader = DataLoader()
    loader.load_raw_data()

    # Strategy 1: Get popular items from transactions
    print("Finding most popular products...")
    popular = loader.transactions_df['article_id'].value_counts().head(1000)
    popular_ids = popular.index.tolist()
    print(f"✓ Found top 1,000 popular items\n")

    # Strategy 2: Get items from each category
    print("Sampling from each category...")
    category_samples = []
    for category in loader.articles_df['product_group_name'].unique()[:20]:
        category_items = loader.articles_df[
            loader.articles_df['product_group_name'] == category
        ]['article_id'].head(25).tolist()
        category_samples.extend(category_items)
    print(f"✓ Sampled {len(category_samples)} items from categories\n")

    # Combine and deduplicate
    all_ids = list(set(popular_ids + category_samples))
    print(f"Total unique items to process: {len(all_ids)}\n")

    # Estimate time
    estimated_minutes = (len(all_ids) * 2) / 60  # ~2 seconds per image
    print(f"⏱️  Estimated time: {estimated_minutes:.1f} minutes\n")

    response = input("Continue with extraction? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    # Extract features
    print("\nExtracting image features...")
    print("This will take 10-15 minutes on CPU...\n")

    extractor = ImageFeatureExtractor()

    # Process in batches with progress
    batch_size = 50
    all_features = {}

    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(all_ids)//batch_size) + 1}...")

        for article_id in batch_ids:
            img_path = loader.get_article_image_path(article_id)
            if img_path and img_path.exists():
                features = extractor.extract_features_from_image(img_path)
                if features is not None:
                    all_features[article_id] = features

        processed = len(all_features)
        percentage = (i / len(all_ids)) * 100
        print(f"  Progress: {percentage:.1f}% - {processed} images processed\n")

    # Save features
    print("\nSaving features...")
    article_ids_list = list(all_features.keys())
    features_array = np.array([all_features[aid] for aid in article_ids_list])

    np.save(IMAGE_FEATURES_NPY, features_array)
    np.save(PROCESSED_DATA_DIR / 'article_ids.npy', article_ids_list)

    print("\n" + "="*60)
    print("✓ Extraction Complete!")
    print("="*60)
    print(f"\nProcessed: {len(all_features)} images")
    print(f"Saved to: {IMAGE_FEATURES_NPY}")
    print(f"\nCoverage: ~{(len(all_features)/105000)*100:.1f}% of catalog")
    print("This covers most items users will actually see!")
    print("\nImage-based recommendations now available! 🎉")
    print("="*60 + "\n")

if __name__ == "__main__":
    extract_smart()