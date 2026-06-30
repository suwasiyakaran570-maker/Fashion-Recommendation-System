import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing import image
from pathlib import Path
from src.config import *
from src.data_loader import DataLoader

class ImageFeatureExtractor:
    def __init__(self):
        # Load pre-trained ResNet50 model
        print("Loading ResNet50 model...")
        self.model = ResNet50(
            weights='imagenet',
            include_top=False,
            pooling='avg'
        )
        print("✓ Model loaded")
        
    def extract_features_from_image(self, img_path):
        """Extract features from a single image"""
        try:
            # Load and preprocess image
            img = image.load_img(img_path, target_size=IMAGE_SIZE)
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = preprocess_input(img_array)
            
            # Extract features
            features = self.model.predict(img_array, verbose=0)
            return features.flatten()
        
        except Exception as e:
            print(f"Error processing {img_path}: {e}")
            return None
    
    def extract_features_batch(self, article_ids, max_images=1000):
        """Extract features from multiple article images"""
        print(f"Extracting features from {min(len(article_ids), max_images)} images...")
        
        loader = DataLoader()
        features_dict = {}
        processed = 0
        
        for article_id in article_ids[:max_images]:
            img_path = loader.get_article_image_path(article_id)
            
            if img_path and img_path.exists():
                features = self.extract_features_from_image(img_path)
                
                if features is not None:
                    features_dict[article_id] = features
                    processed += 1
                    
                    if processed % 100 == 0:
                        print(f"Processed {processed} images...")
        
        print(f"✓ Extracted features from {processed} images")
        
        # Convert to numpy array
        article_ids_list = list(features_dict.keys())
        features_array = np.array([features_dict[aid] for aid in article_ids_list])
        
        # Save features
        np.save(IMAGE_FEATURES_NPY, features_array)
        np.save(PROCESSED_DATA_DIR / 'article_ids.npy', article_ids_list)
        
        print(f"✓ Saved features to {IMAGE_FEATURES_NPY}")
        
        return features_array, article_ids_list
    
    def get_similar_images(self, query_article_id, top_n=10):
        """Find similar images based on visual features"""
        try:
            # Load saved features
            features_array = np.load(IMAGE_FEATURES_NPY)
            article_ids = np.load(PROCESSED_DATA_DIR / 'article_ids.npy')
            
            # Get query image features
            loader = DataLoader()
            query_img_path = loader.get_article_image_path(query_article_id)
            
            if not query_img_path or not query_img_path.exists():
                return []
            
            query_features = self.extract_features_from_image(query_img_path)
            
            if query_features is None:
                return []
            
            # Calculate cosine similarity
            similarities = np.dot(features_array, query_features) / (
                np.linalg.norm(features_array, axis=1) * np.linalg.norm(query_features)
            )
            
            # Get top N similar items
            top_indices = np.argsort(similarities)[::-1][1:top_n+1]
            similar_article_ids = article_ids[top_indices].tolist()
            
            return similar_article_ids
        
        except Exception as e:
            print(f"Error finding similar images: {e}")
            return []

if __name__ == "__main__":
    # Example usage
    extractor = ImageFeatureExtractor()
    
    # Load some article IDs
    loader = DataLoader()
    loader.load_raw_data()
    article_ids = loader.articles_df['article_id'].head(500).tolist()
    
    # Extract features
    extractor.extract_features_batch(article_ids)