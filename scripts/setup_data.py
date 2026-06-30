#setup_data.py
import sys
from pathlib import Path

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.preprocessing import DataPreprocessor
from src.recommender import FashionRecommender
from src.image_model import ImageFeatureExtractor
from src.data_loader import DataLoader

def main():
    print("\n" + "="*60)
    print("H&M Fashion Recommendation System - Data Setup")
    print("="*60 + "\n")
    
    # Step 1: Check if data files exist
    print("Step 1: Checking data files...")
    from src.config import ARTICLES_CSV, CUSTOMERS_CSV, TRANSACTIONS_CSV
    
    missing_files = []
    if not ARTICLES_CSV.exists():
        missing_files.append(str(ARTICLES_CSV))
    if not CUSTOMERS_CSV.exists():
        missing_files.append(str(CUSTOMERS_CSV))
    if not TRANSACTIONS_CSV.exists():
        missing_files.append(str(TRANSACTIONS_CSV))
    
    if missing_files:
        print("\n❌ ERROR: Missing required data files:")
        for f in missing_files:
            print(f"  - {f}")
        print("\nPlease place your H&M dataset files in the data/raw/ directory")
        print("Required files:")
        print("  - articles.csv")
        print("  - customers.csv")
        print("  - transactions_train.csv")
        print("  - images/ folder with product images")
        return
    
    print("✓ All required files found!\n")
    
    # Step 2: Preprocess data
    print("Step 2: Preprocessing data...")
    preprocessor = DataPreprocessor()
    try:
        preprocessor.run_full_preprocessing()
        print("✓ Preprocessing complete!\n")
    except Exception as e:
        print(f"✗ Error during preprocessing: {e}\n")
    
    # Step 3: Build recommendation model
    print("Step 3: Building recommendation model...")
    try:
        recommender = FashionRecommender()
        recommender.build_collaborative_filtering()
        recommender.save_model()
        print("✓ Recommendation model built and saved!\n")
    except Exception as e:
        print(f"✗ Error building model: {e}\n")
    
    # Step 4: Extract image features (optional - can be slow)
    print("Step 4: Extract image features?")
    print("Note: This step is optional and can take a while.")
    response = input("Do you want to extract image features now? (y/n): ")
    
    if response.lower() == 'y':
        print("\nExtracting image features...")
        try:
            extractor = ImageFeatureExtractor()
            loader = DataLoader()
            loader.load_raw_data()
            
            # Extract features from first 500 articles
            article_ids = loader.articles_df['article_id'].head(500).tolist()
            extractor.extract_features_batch(article_ids)
            print("✓ Image features extracted!\n")
        except Exception as e:
            print(f"✗ Error extracting features: {e}\n")
    else:
        print("Skipping image feature extraction.\n")
    
    print("="*60)
    print("Setup Complete!")
    print("="*60)
    print("\nYou can now run the application with:")
    print("  python run.py")
    print("\nOr manually with:")
    print("  python -m app.app")
    print()

if __name__ == "__main__":
    main()