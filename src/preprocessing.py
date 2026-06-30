import pandas as pd
import numpy as np
from pathlib import Path
from src.config import *
from src.data_loader import DataLoader

class DataPreprocessor:
    def __init__(self):
        self.loader = DataLoader()
        
    def merge_datasets(self):
        """Merge articles, customers, and transactions"""
        print("Merging datasets...")
        
        self.loader.load_raw_data()
        
        # Use a SMALL sample of transactions to save memory
        print("Sampling transactions for memory efficiency...")
        sample_size = min(50000, len(self.loader.transactions_df))  # Only 50K transactions
        transactions_sample = self.loader.transactions_df.sample(n=sample_size, random_state=42)
        print(f"Using {sample_size:,} transactions (sampled from {len(self.loader.transactions_df):,})")
        
        # Merge transactions with articles
        merged = pd.merge(
            transactions_sample,
            self.loader.articles_df,
            on='article_id',
            how='left'
        )
        
        # Don't merge customers - not needed for basic recommendations
        print("Skipping customer merge to save memory...")
        
        # Save merged data
        merged.to_csv(MERGED_DATA_CSV, index=False)
        print(f"✓ Saved merged data: {len(merged):,} records")
        
        return merged
    
    def create_user_item_matrix(self):
        """Create user-item interaction matrix"""
        print("Creating user-item matrix...")
        
        if not MERGED_DATA_CSV.exists():
            merged = self.merge_datasets()
        else:
            print("Loading existing merged data...")
            merged = pd.read_csv(MERGED_DATA_CSV)
        
        # Use VERY small sample for memory efficiency
        sample_size = min(10000, len(merged))  # Only 10K records
        merged_sample = merged.sample(n=sample_size, random_state=42)
        print(f"Using {sample_size:,} records for matrix (sampled from {len(merged):,})")
        
        # Create interaction matrix (user x item)
        # Group by to reduce size
        interaction_counts = merged_sample.groupby(['customer_id', 'article_id']).size().reset_index(name='count')
        
        # Create smaller pivot
        user_item = interaction_counts.pivot_table(
            index='customer_id',
            columns='article_id',
            values='count',
            fill_value=0
        )
        
        # Limit to top users and items only
        max_users = 500
        max_items = 500
        
        if len(user_item) > max_users:
            user_item = user_item.head(max_users)
        if len(user_item.columns) > max_items:
            user_item = user_item.iloc[:, :max_items]
        
        print(f"✓ Created matrix: {user_item.shape[0]} users × {user_item.shape[1]} items")
        return user_item
    
    def get_article_features(self):
        """Extract and encode article features"""
        print("Extracting article features...")
        
        self.loader.load_raw_data()
        articles = self.loader.articles_df
        
        # Select relevant features
        feature_cols = [
            'product_type_no', 'graphical_appearance_no', 
            'colour_group_code', 'perceived_colour_value_id',
            'perceived_colour_master_id', 'department_no',
            'index_code', 'index_group_no', 'section_no',
            'garment_group_no'
        ]
        
        features = articles[['article_id'] + feature_cols].copy()
        
        # Fill missing values
        features = features.fillna(0)
        
        return features
    
    def run_full_preprocessing(self):
        """Run complete preprocessing pipeline"""
        print("\n" + "="*50)
        print("Starting Full Preprocessing Pipeline")
        print("="*50 + "\n")
        
        # Step 1: Merge datasets
        merged = self.merge_datasets()
        
        # Step 2: Create user-item matrix
        user_item = self.create_user_item_matrix()
        
        # Step 3: Extract features
        features = self.get_article_features()
        
        print("\n" + "="*50)
        print("Preprocessing Complete!")
        print("="*50 + "\n")
        
        return {
            'merged': merged,
            'user_item': user_item,
            'features': features
        }

if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.run_full_preprocessing()