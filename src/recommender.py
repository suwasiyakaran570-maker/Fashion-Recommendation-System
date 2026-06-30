"""
src/recommender.py  –  Gender-aware fashion recommender
========================================================
Changes from original:
  1. get_hybrid_recommendations() now accepts an optional `gender` parameter.
  2. When gender is provided, collaborative-filtering candidates are filtered
     so only items from matching Men/Women sections are returned.
  3. A complementary-item layer (via DataLoader.get_complementary_articles())
     is blended into the final output: ~40 % complementary, ~60 % similar.
  4. The method signature is BACKWARDS-COMPATIBLE — existing callers that pass
     only (article_id, n) still work; gender defaults to None (no filter).

Impact on other files:
  • product_detail route in app.py passes the current article's detected gender
    into this method automatically → no template change needed.
  • search_results.html and index.html are NOT affected because they don't call
    this method; they use DataLoader.search_articles() / get_popular_articles()
    which handle gender independently.
"""

import numpy as np
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import *


# Gender keyword sets (mirrored from data_loader for self-contained filtering)
_MALE_KW   = {'men', 'mens', "men's", 'boy', 'boys'}
_FEMALE_KW = {'women', 'womens', "women's", 'lady', 'ladies', 'girl', 'girls', 'woman'}


class FashionRecommender:
    def __init__(self):
        self.similarity_matrix = None
        self.article_ids = None
        self.articles_df = None  # reference to DataLoader's df, set at load time

    # ── Model loading ────────────────────────────────────────────────────────
    def load_model(self):
        """
        Load pre-computed similarity matrix (.npy) and article ID index (.npy).
        If files don't exist, fall back to a stub that returns empty results.
        """
        try:
            sim_path = BASE_DIR / 'models' / 'similarity_matrix.npy'
            ids_path = BASE_DIR / 'models' / 'article_ids.npy'

            if sim_path.exists() and ids_path.exists():
                self.similarity_matrix = np.load(sim_path, allow_pickle=True)
                self.article_ids = np.load(ids_path, allow_pickle=True)
                print(f"✓ Loaded similarity matrix: {self.similarity_matrix.shape}")
            else:
                print("⚠ Similarity matrix not found – recommender will use complementary-only mode.")
                self.similarity_matrix = None
                self.article_ids = None
        except Exception as e:
            print(f"⚠ Error loading recommender model: {e}")
            self.similarity_matrix = None
            self.article_ids = None

    def set_articles_df(self, articles_df):
        """Inject the articles DataFrame (called once by app.py after DataLoader loads)."""
        self.articles_df = articles_df

    # ── Internal helpers ─────────────────────────────────────────────────────
    def _get_gender_from_article(self, article_id) -> str | None:
        """Detect Men/Women from a single article's section_name / department_name."""
        if self.articles_df is None:
            return None
        row = self.articles_df[self.articles_df['article_id'] == article_id]
        if row.empty:
            return None
        section = str(row.iloc[0].get('section_name', '')).lower()
        dept    = str(row.iloc[0].get('department_name', '')).lower()

        for kw in _MALE_KW:
            if kw in section or kw in dept:
                return 'Men'
        for kw in _FEMALE_KW:
            if kw in section or kw in dept:
                return 'Women'
        return None

    def _gender_mask(self, candidate_ids, gender: str):
        """Return subset of candidate_ids that match the given gender."""
        if self.articles_df is None or gender is None:
            return candidate_ids

        keywords = _MALE_KW if gender == 'Men' else _FEMALE_KW
        pattern  = '|'.join(keywords)

        subset = self.articles_df[self.articles_df['article_id'].isin(candidate_ids)]
        mask = (
            subset['section_name'].str.contains(pattern, case=False, na=False, regex=True) |
            subset['department_name'].str.contains(pattern, case=False, na=False, regex=True)
        )
        return subset.loc[mask, 'article_id'].tolist()

    def _similarity_based_recs(self, article_id, n=10) -> list[int]:
        """Pure collaborative-filtering recommendations from the similarity matrix."""
        if self.similarity_matrix is None or self.article_ids is None:
            return []

        try:
            idx = np.where(self.article_ids == article_id)[0]
            if len(idx) == 0:
                return []
            idx = idx[0]

            # Get top-n+1 most similar (first one is the item itself)
            sim_scores = self.similarity_matrix[idx]
            top_indices = np.argsort(sim_scores)[::-1][1:n + 1]
            return [int(self.article_ids[i]) for i in top_indices]
        except Exception:
            return []

    # ── Public API ───────────────────────────────────────────────────────────
    def get_hybrid_recommendations(self, article_id, n=6, gender=None) -> list[int]:
        """
        Returns up to `n` recommended article IDs using a blend of:
          • Similarity-based (collaborative filtering) – 60 %
          • Complementary items (from DataLoader)     – 40 %

        Gender filtering:
          - If `gender` is not passed, it is auto-detected from the source article.
          - Similarity candidates are filtered to the same gender.
          - Complementary items already handle gender internally.

        Parameters
        ----------
        article_id : int
            The product the user is currently viewing.
        n : int
            How many recommendations to return (default 6).
        gender : str | None
            'Men', 'Women', or None (auto-detect).

        Returns
        -------
        list[int]
            Article IDs of recommended products.
        """
        # Auto-detect gender from the source article if not provided
        if gender is None:
            gender = self._get_gender_from_article(article_id)

        # ── Layer 1: similarity-based ────────────────────────────────────
        n_similar = max(1, int(n * 0.6))   # 60 % similar
        n_comp    = n - n_similar           # 40 % complementary

        similar_ids = self._similarity_based_recs(article_id, n=n_similar + 5)  # over-fetch

        # Filter similar items by gender
        if gender and similar_ids:
            filtered = self._gender_mask(similar_ids, gender)
            if filtered:
                similar_ids = filtered
        similar_ids = similar_ids[:n_similar]

        # ── Layer 2: complementary items ─────────────────────────────────
        # Import here to avoid circular import at module level
        comp_ids = []
        try:
            from src.data_loader import DataLoader
            dl = DataLoader()
            dl.load_raw_data()
            comp_articles = dl.get_complementary_articles(article_id, n=n_comp + 3)
            comp_ids = [a['article_id'] for a in comp_articles][:n_comp]
        except Exception as e:
            print(f"⚠ Complementary lookup failed: {e}")

        # ── Merge & deduplicate ──────────────────────────────────────────
        seen = {article_id}  # never recommend the item itself
        final = []
        for aid in similar_ids + comp_ids:
            if aid not in seen:
                seen.add(aid)
                final.append(aid)
            if len(final) >= n:
                break

        # If we still have room and have no similarity matrix, fill from complementary
        if len(final) < n and not similar_ids:
            # Already have comp_ids; nothing more to do without similarity data
            pass

        return final 