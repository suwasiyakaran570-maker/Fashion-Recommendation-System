import pandas as pd
import numpy as np
from pathlib import Path
from src.config import *

# ── Gender keyword mappings ──────────────────────────────────────────────────
MALE_KEYWORDS = [
    'men', 'mens', "men's", 'boy', 'boys', "boy's",
    'male', 'him', 'his'
]

FEMALE_KEYWORDS = [
    'women', 'womens', "women's", 'lady', 'ladies',
    'girl', 'girls', "girl's", 'woman',
    'female', 'her', 'she'
]

# ── ENHANCED Complementary item map ──────────────────────────────────────────
# Maps product/garment types to what should be recommended together
# Key = current item's category (lowercase)
# Value = dict with 'garment_groups' and 'product_types' to match

COMPLEMENTARY_RULES = {
    # Shirts / Upper body → Pants, Shoes, Belts, Watches
    'shirt': {
        'garment_groups': ['trousers', 'shorts', 'shoes', 'socks & tights'],
        'product_types': ['trousers', 'shorts', 'sneakers', 'shoes', 'belt', 'watch', 'tie', 'socks'],
        'accessories': True
    },
    'blouse': {
        'garment_groups': ['trousers', 'skirt', 'shoes', 'socks & tights'],
        'product_types': ['trousers', 'skirt', 'shoes', 'belt', 'watch', 'bag', 'jewellery'],
        'accessories': True
    },
    'sweater': {
        'garment_groups': ['trousers', 'skirt', 'shoes'],
        'product_types': ['jeans', 'trousers', 'skirt', 'sneakers', 'boots'],
        'accessories': True
    },
    't-shirt': {
        'garment_groups': ['trousers', 'shorts', 'shoes'],
        'product_types': ['jeans', 'shorts', 'sneakers', 'cap', 'watch'],
        'accessories': True
    },
    'top': {
        'garment_groups': ['trousers', 'skirt', 'shoes'],
        'product_types': ['jeans', 'skirt', 'heels', 'sneakers', 'bag'],
        'accessories': True
    },
    
    # Pants / Lower body → Shirts, Shoes, Belts
    'trousers': {
        'garment_groups': ['shirt', 'jersey', 'shoes'],
        'product_types': ['shirt', 'blouse', 't-shirt', 'shoes', 'belt', 'watch'],
        'accessories': True
    },
    'jeans': {
        'garment_groups': ['jersey', 'shoes', 'under, jersey, accessories'],
        'product_types': ['t-shirt', 'shirt', 'sneakers', 'boots', 'belt'],
        'accessories': True
    },
    'shorts': {
        'garment_groups': ['jersey', 'shoes'],
        'product_types': ['t-shirt', 'polo shirt', 'sneakers', 'cap'],
        'accessories': True
    },
    'skirt': {
        'garment_groups': ['jersey', 'shoes', 'under, jersey, accessories'],
        'product_types': ['blouse', 'top', 'heels', 'sandal', 'bag'],
        'accessories': True
    },
    
    # Dresses / Full body → Shoes, Bags, Jewelry
    'dress': {
        'garment_groups': ['shoes', 'under, jersey, accessories'],
        'product_types': ['heels', 'sandal', 'bag', 'jewellery', 'belt'],
        'accessories': True
    },
    
    # Shoes → Everything except shoes
    'shoes': {
        'garment_groups': ['jersey', 'trousers', 'under, jersey, accessories'],
        'product_types': ['shirt', 'trousers', 'jeans', 'socks', 'belt'],
        'accessories': True
    },
    'sneakers': {
        'garment_groups': ['jersey', 'trousers'],
        'product_types': ['t-shirt', 'jeans', 'shorts', 'socks', 'cap'],
        'accessories': True
    },
    
    # Accessories → Upper + Lower
    'accessories': {
        'garment_groups': ['jersey', 'trousers', 'shoes'],
        'product_types': ['shirt', 'trousers', 'shoes'],
        'accessories': False  # Don't recommend accessories for accessories
    },
}


class DataLoader:
    def __init__(self):
        self.articles_df = None
        self.customers_df = None
        self.transactions_df = None

    # ── Loading ──────────────────────────────────────────────────────────────
    def load_raw_data(self):
        """Load raw CSV files"""
        print("Loading raw data...")

        try:
            self.articles_df = pd.read_csv(ARTICLES_CSV)
            print(f"✓ Loaded {len(self.articles_df)} articles")
        except Exception as e:
            print(f"✗ Error loading articles: {e}")

        try:
            self.customers_df = pd.read_csv(CUSTOMERS_CSV)
            print(f"✓ Loaded {len(self.customers_df)} customers")
        except Exception as e:
            print(f"✗ Error loading customers: {e}")

        try:
            self.transactions_df = pd.read_csv(TRANSACTIONS_CSV)
            print(f"✓ Loaded {len(self.transactions_df)} transactions")
        except Exception as e:
            print(f"✗ Error loading transactions: {e}")

        return self

    def _ensure_loaded(self):
        if self.articles_df is None:
            self.load_raw_data()

    # ── Single article ───────────────────────────────────────────────────────
    def get_article_by_id(self, article_id):
        self._ensure_loaded()
        article = self.articles_df[self.articles_df['article_id'] == article_id]
        if len(article) > 0:
            article_dict = article.iloc[0].to_dict()
            if 'price' not in article_dict or pd.isna(article_dict.get('price')):
                article_dict['price'] = self._generate_price(article_dict)
            return article_dict
        return None

    # ── Price generation ─────────────────────────────────────────────────────
    def _generate_price(self, article):
        import random
        price_ranges = {
            'Garment Upper body': (799, 2999),
            'Garment Lower body': (999, 3499),
            'Garment Full body': (1499, 5999),
            'Shoes': (1999, 4999),
            'Accessories': (299, 1999),
            'Underwear/nightwear': (499, 1499),
            'Bags': (999, 3999),
            'Cosmetic': (299, 999),
            'Furniture': (4999, 14999),
            'Interior textile': (799, 2999),
            'Fun': (299, 1499),
        }
        product_group = article.get('product_group_name', 'Unknown')
        min_price, max_price = price_ranges.get(product_group, (799, 2499))
        random.seed(article.get('article_id', 0))
        return round(random.uniform(min_price, max_price), 2)

    # ── Image helpers ────────────────────────────────────────────────────────
    def get_article_image_path(self, article_id):
        image_id = f"0{int(article_id)}"
        folder = image_id[:3]
        image_path = IMAGES_DIR / folder / f"{image_id}.jpg"
        return image_path if image_path.exists() else None

    def get_article_image_url(self, article_id):
        img_path = self.get_article_image_path(article_id)
        if img_path and img_path.exists():
            relative_path = img_path.relative_to(BASE_DIR)
            return '/' + str(relative_path).replace('\\', '/')

        self._ensure_loaded()
        article = self.articles_df[self.articles_df['article_id'] == article_id]
        if len(article) > 0:
            color_id = article.iloc[0].get('perceived_colour_value_id', 1)
            product_type = str(article.iloc[0].get('product_type_name', 'Fashion'))
            colors = {
                1: ('#FF6B6B', '#fff'), 2: ('#4ECDC4', '#fff'),
                3: ('#95E1D3', '#333'), 4: ('#FFA07A', '#fff'),
                5: ('#DDA15E', '#fff'), 6: ('#6C757D', '#fff'),
                7: ('#2C3E50', '#fff'), 8: ('#A8D8EA', '#333'),
                9: ('#F7DC6F', '#333'),
            }
            bg, txt = colors.get(int(color_id) if color_id else 1, colors[1])
            return self._svg_placeholder(bg, txt, product_type)

        return self._svg_placeholder('#cccccc', '#666666', 'No Image')

    def _svg_placeholder(self, bg_color, text_color, label):
        import urllib.parse
        safe_label = label.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="500" viewBox="0 0 400 500">'
            f'<rect width="400" height="500" fill="{bg_color}" rx="8"/>'
            f'<rect x="140" y="160" width="120" height="120" rx="12" fill="rgba(255,255,255,0.15)"/>'
            f'<text x="200" y="240" text-anchor="middle" font-family="Arial,sans-serif" font-size="48" fill="rgba(255,255,255,0.4)">&#128197;</text>'
            f'<text x="200" y="370" text-anchor="middle" font-family="Arial,sans-serif" font-size="22" fill="{text_color}" font-weight="600">{safe_label}</text>'
            f'<text x="200" y="398" text-anchor="middle" font-family="Arial,sans-serif" font-size="13" fill="{text_color}" opacity="0.6">No Image Available</text>'
            f'</svg>'
        )
        return f'data:image/svg+xml,{urllib.parse.quote(svg)}'

    # ── Gender detection helper ──────────────────────────────────────────────
    @staticmethod
    def _detect_gender_from_query(query: str) -> str | None:
        q = query.lower()
        for kw in MALE_KEYWORDS:
            if kw in q.split() or kw in q:
                return 'Men'
        for kw in FEMALE_KEYWORDS:
            if kw in q.split() or kw in q:
                return 'Women'
        return None

    @staticmethod
    def _gender_mask(df: pd.DataFrame, gender: str) -> pd.Series:
        if gender == 'Men':
            keywords = MALE_KEYWORDS
        elif gender == 'Women':
            keywords = FEMALE_KEYWORDS
        else:
            return pd.Series([True] * len(df), index=df.index)

        pattern = '|'.join(keywords)
        section_match = df['section_name'].str.contains(pattern, case=False, na=False, regex=True)
        dept_match   = df['department_name'].str.contains(pattern, case=False, na=False, regex=True)
        return section_match | dept_match

    # ── Popular articles ─────────────────────────────────────────────────────
    def get_popular_articles(self, n=20, gender=None):
        self._ensure_loaded()
        popular = self.transactions_df['article_id'].value_counts().head(n * 3)
        article_ids = popular.index.tolist()
        articles = self.articles_df[self.articles_df['article_id'].isin(article_ids)].copy()

        if gender and gender in ('Men', 'Women'):
            mask = self._gender_mask(articles, gender)
            articles = articles[mask]

        articles = articles.sample(frac=1, random_state=None)  # shuffle all rows

        articles = articles.head(n)
        articles_list = articles.to_dict('records')

        for article in articles_list:
            if 'price' not in article or pd.isna(article.get('price')):
                article['price'] = self._generate_price(article)

        return articles_list

    # ── Search with gender awareness ─────────────────────────────────────────
    def search_articles(self, query, n=50, gender=None):
        self._ensure_loaded()
        query_lower = query.lower().strip()
        detected_gender = gender or self._detect_gender_from_query(query_lower)

        mask = (
            self.articles_df['prod_name'].str.contains(query_lower, case=False, na=False) |
            self.articles_df['product_type_name'].str.contains(query_lower, case=False, na=False) |
            self.articles_df['product_group_name'].str.contains(query_lower, case=False, na=False) |
            self.articles_df['section_name'].str.contains(query_lower, case=False, na=False) |
            self.articles_df['garment_group_name'].str.contains(query_lower, case=False, na=False)
        )

        articles = self.articles_df[mask].copy()

        if detected_gender:
            gender_mask = self._gender_mask(articles, detected_gender)
            filtered = articles[gender_mask]
            if len(filtered) > 0:
                articles = filtered

        articles = articles.head(n)
        articles_list = articles.to_dict('records')

        for article in articles_list:
            if 'price' not in article or pd.isna(article.get('price')):
                article['price'] = self._generate_price(article)

        return articles_list, detected_gender

    # ── Get articles by category ─────────────────────────────────────────────
    def get_articles_by_category(self, category, n=20, gender=None):
        self._ensure_loaded()
        mask = (
            self.articles_df['product_group_name'].str.contains(category, case=False, na=False) |
            self.articles_df['product_type_name'].str.contains(category, case=False, na=False) |
            self.articles_df['section_name'].str.contains(category, case=False, na=False)
        )
        articles = self.articles_df[mask].copy()

        if gender and gender in ('Men', 'Women'):
            gender_mask = self._gender_mask(articles, gender)
            filtered = articles[gender_mask]
            if len(filtered) > 0:
                articles = filtered

        articles = articles.head(n)
        articles_list = articles.to_dict('records')

        for article in articles_list:
            if 'price' not in article or pd.isna(article.get('price')):
                article['price'] = self._generate_price(article)

        return articles_list

    # ── ENHANCED Complementary items ─────────────────────────────────────────
    def get_complementary_articles(self, article_id, n=6):
        """
        ENHANCED: For a shirt, returns pants, shoes, belts, watches, accessories.
        Uses detailed product_type_name matching for better results.
        """
        self._ensure_loaded()

        source = self.get_article_by_id(article_id)
        if not source:
            return []

        # Get source item details
        source_product_type = str(source.get('product_type_name', '')).lower().strip()
        source_garment = str(source.get('garment_group_name', '')).lower().strip()
        source_product_group = str(source.get('product_group_name', '')).lower().strip()

        # Detect gender
        source_gender = None
        section = str(source.get('section_name', '')).lower()
        dept = str(source.get('department_name', '')).lower()
        for kw in MALE_KEYWORDS:
            if kw in section or kw in dept:
                source_gender = 'Men'
                break
        if not source_gender:
            for kw in FEMALE_KEYWORDS:
                if kw in section or kw in dept:
                    source_gender = 'Women'
                    break

        # Find matching rule
        rules = None
        for key, rule in COMPLEMENTARY_RULES.items():
            if key in source_product_type or key in source_garment or key in source_product_group:
                rules = rule
                break

        if not rules:
            # Fallback: generic upper→lower, lower→upper
            if 'upper' in source_product_group or 'shirt' in source_product_type or 'jersey' in source_garment:
                rules = COMPLEMENTARY_RULES.get('shirt')
            elif 'lower' in source_product_group or 'trouser' in source_product_type:
                rules = COMPLEMENTARY_RULES.get('trousers')
            elif 'shoes' in source_product_group:
                rules = COMPLEMENTARY_RULES.get('shoes')
            else:
                rules = {'garment_groups': ['shoes'], 'product_types': ['shoes'], 'accessories': True}

        # Build search mask
        candidates_mask = pd.Series([False] * len(self.articles_df), index=self.articles_df.index)

        # Match by product_type_name (most specific)
        if 'product_types' in rules:
            for ptype in rules['product_types']:
                candidates_mask |= self.articles_df['product_type_name'].str.contains(
                    ptype, case=False, na=False, regex=False
                )

        # Match by garment_group_name
        if 'garment_groups' in rules:
            for gg in rules['garment_groups']:
                candidates_mask |= self.articles_df['garment_group_name'].str.contains(
                    gg, case=False, na=False, regex=False
                )

        # Add accessories if enabled
        if rules.get('accessories'):
            candidates_mask |= self.articles_df['product_group_name'].str.contains(
                'accessories', case=False, na=False
            )

        candidates = self.articles_df[candidates_mask].copy()

        # Filter by gender
        if source_gender:
            gender_mask = self._gender_mask(candidates, source_gender)
            filtered = candidates[gender_mask]
            if len(filtered) > 0:
                candidates = filtered

        # Exclude source item
        candidates = candidates[candidates['article_id'] != article_id]

        # Sample
        if len(candidates) > n:
            candidates = candidates.sample(n=n, random_state=article_id)
        else:
            candidates = candidates.head(n)

        results = candidates.to_dict('records')
        for article in results:
            if 'price' not in article or pd.isna(article.get('price')):
                article['price'] = self._generate_price(article)

        return results

    # ── Customer history ─────────────────────────────────────────────────────
    def get_customer_history(self, customer_id):
        self._ensure_loaded()
        customer_trans = self.transactions_df[self.transactions_df['customer_id'] == customer_id]
        article_ids = customer_trans['article_id'].unique().tolist()
        articles = self.articles_df[self.articles_df['article_id'].isin(article_ids)]
        articles_list = articles.to_dict('records')
        for article in articles_list:
            if 'price' not in article or pd.isna(article.get('price')):
                article['price'] = self._generate_price(article)
        return articles_list

    # ── OUTFIT RECOMMENDATIONS ──────────────────────────────────────────────
    def get_complete_outfits(self, article_id, n=3):
        """
        Generate complete outfit recommendations.
        Each outfit contains: top, bottom, shoes, and accessories.
        
        Returns:
            List of outfit dicts, each containing:
            - outfit_name: str (e.g., "Business Casual", "Weekend Vibes")
            - items: list of article dicts
            - total_price: float
        """
        self._ensure_loaded()
        
        source = self.get_article_by_id(article_id)
        if not source:
            return []
        
        # Detect gender
        source_gender = self._detect_article_gender(source)
        
        # Determine what type of item this is
        source_type = self._classify_item_type(source)
        
        # Generate outfits based on source type
        outfits = []
        
        if source_type == 'top':
            # Build outfits around this top
            outfits = self._build_outfits_from_top(source, source_gender, n)
        elif source_type == 'bottom':
            # Build outfits around this bottom
            outfits = self._build_outfits_from_bottom(source, source_gender, n)
        elif source_type == 'shoes':
            # Build outfits around these shoes
            outfits = self._build_outfits_from_shoes(source, source_gender, n)
        elif source_type == 'dress':
            # Dress + shoes + accessories
            outfits = self._build_outfits_from_dress(source, source_gender, n)
        else:
            # For accessories, show complete outfits that include this accessory
            outfits = self._build_outfits_with_accessory(source, source_gender, n)
        
        return outfits
    
    def _detect_article_gender(self, article):
        """Detect gender from article's section/department"""
        section = str(article.get('section_name', '')).lower()
        dept = str(article.get('department_name', '')).lower()
        
        for kw in MALE_KEYWORDS:
            if kw in section or kw in dept:
                return 'Men'
        for kw in FEMALE_KEYWORDS:
            if kw in section or kw in dept:
                return 'Women'
        return None
    
    def _classify_item_type(self, article):
        """Classify article into: top, bottom, shoes, dress, accessory"""
        product_group = str(article.get('product_group_name', '')).lower()
        product_type = str(article.get('product_type_name', '')).lower()
        garment_group = str(article.get('garment_group_name', '')).lower()
        
        # Check for dress (full body)
        if 'dress' in product_type or 'full body' in product_group:
            return 'dress'
        
        # Check for shoes
        if 'shoes' in product_group or 'shoes' in garment_group:
            return 'shoes'
        
        # Check for upper body (tops)
        if any(x in product_group for x in ['upper body', 'garment upper']):
            return 'top'
        if any(x in product_type for x in ['shirt', 'blouse', 't-shirt', 'top', 'sweater', 'jacket']):
            return 'top'
        if any(x in garment_group for x in ['jersey', 'knitwear', 'shirt']):
            return 'top'
        
        # Check for lower body (bottoms)
        if any(x in product_group for x in ['lower body', 'garment lower']):
            return 'bottom'
        if any(x in product_type for x in ['trouser', 'jeans', 'shorts', 'skirt']):
            return 'bottom'
        if 'trousers' in garment_group or 'shorts' in garment_group:
            return 'bottom'
        
        # Everything else is accessory
        return 'accessory'
    
    def _detect_item_style(self, article):
        """
        Detect the style/occasion of an item: formal, casual, sporty, elegant
        """
        product_type = str(article.get('product_type_name', '')).lower()
        product_name = str(article.get('prod_name', '')).lower()
        section = str(article.get('section_name', '')).lower()
        garment = str(article.get('garment_group_name', '')).lower()
        
        # Formal indicators
        formal_keywords = ['suit', 'blazer', 'formal', 'dress shirt', 'oxford', 'tie', 
                          'dress shoes', 'loafer', 'heel', 'office', 'business', 'trouser']
        
        # Casual indicators
        casual_keywords = ['t-shirt', 'tee', 'jeans', 'casual', 'denim', 'sneaker', 
                          'hoodie', 'sweatshirt', 'polo', 'chino']
        
        # Sporty/Active indicators
        sporty_keywords = ['sport', 'active', 'gym', 'running', 'training', 'athletic',
                          'jogger', 'track', 'shorts', 'trainers']
        
        # Elegant/Evening indicators
        elegant_keywords = ['dress', 'gown', 'cocktail', 'evening', 'elegant', 'satin',
                           'silk', 'velvet', 'party', 'occasion']
        
        combined_text = f"{product_type} {product_name} {section} {garment}"
        
        # Score each style
        formal_score = sum(1 for kw in formal_keywords if kw in combined_text)
        casual_score = sum(1 for kw in casual_keywords if kw in combined_text)
        sporty_score = sum(1 for kw in sporty_keywords if kw in combined_text)
        elegant_score = sum(1 for kw in elegant_keywords if kw in combined_text)
        
        # Determine dominant style
        scores = {
            'formal': formal_score,
            'casual': casual_score,
            'sporty': sporty_score,
            'elegant': elegant_score
        }
        
        max_score = max(scores.values())
        if max_score == 0:
            return 'casual'  # Default to casual if uncertain
        
        # Return the style with highest score
        return max(scores, key=scores.get)
    
    def _build_outfits_from_top(self, top_article, gender, n=3):
        """Build complete outfits starting with a top - CONTEXT AWARE"""
        outfits = []
        
        # Detect the style of this top
        style = self._detect_item_style(top_article)
        
        # Define outfit themes based on style and gender
        if style == 'formal':
            outfit_themes = [
                ('Business Professional', {'bottom': 'trousers', 'shoes': 'dress shoes', 'accessory': 'watch'}),
                ('Executive Look', {'bottom': 'formal trousers', 'shoes': 'oxford shoes', 'accessory': 'tie'}),
                ('Office Ready', {'bottom': 'suit trousers', 'shoes': 'loafer', 'accessory': 'belt'}),
            ] if gender == 'Men' else [
                ('Corporate Chic', {'bottom': 'trousers', 'shoes': 'heels', 'accessory': 'bag'}),
                ('Boardroom Ready', {'bottom': 'pencil skirt', 'shoes': 'pumps', 'accessory': 'watch'}),
                ('Professional Edge', {'bottom': 'formal trousers', 'shoes': 'heels', 'accessory': 'blazer'}),
            ]
        
        elif style == 'sporty':
            outfit_themes = [
                ('Gym Ready', {'bottom': 'joggers', 'shoes': 'trainers', 'accessory': 'cap'}),
                ('Athletic Style', {'bottom': 'track pants', 'shoes': 'running shoes', 'accessory': 'sports watch'}),
                ('Active Wear', {'bottom': 'shorts', 'shoes': 'sneakers', 'accessory': 'gym bag'}),
            ] if gender == 'Men' else [
                ('Workout Vibes', {'bottom': 'leggings', 'shoes': 'trainers', 'accessory': 'sports bag'}),
                ('Athletic Chic', {'bottom': 'yoga pants', 'shoes': 'running shoes', 'accessory': 'headband'}),
                ('Fitness Style', {'bottom': 'shorts', 'shoes': 'sneakers', 'accessory': 'water bottle'}),
            ]
        
        elif style == 'elegant':
            outfit_themes = [
                ('Evening Sophisticate', {'bottom': 'dress trousers', 'shoes': 'dress shoes', 'accessory': 'watch'}),
                ('Night Out', {'bottom': 'chinos', 'shoes': 'loafers', 'accessory': 'belt'}),
            ] if gender == 'Men' else [
                ('Date Night', {'bottom': 'skirt', 'shoes': 'heels', 'accessory': 'clutch'}),
                ('Evening Elegance', {'bottom': 'trousers', 'shoes': 'heels', 'accessory': 'jewellery'}),
                ('Cocktail Ready', {'bottom': 'midi skirt', 'shoes': 'sandals', 'accessory': 'bag'}),
            ]
        
        else:  # casual (default)
            outfit_themes = [
                ('Weekend Casual', {'bottom': 'jeans', 'shoes': 'sneakers', 'accessory': 'cap'}),
                ('Everyday Comfort', {'bottom': 'chinos', 'shoes': 'casual shoes', 'accessory': 'watch'}),
                ('Relaxed Style', {'bottom': 'shorts', 'shoes': 'loafers', 'accessory': 'belt'}),
            ] if gender == 'Men' else [
                ('Casual Chic', {'bottom': 'jeans', 'shoes': 'sneakers', 'accessory': 'bag'}),
                ('Brunch Ready', {'bottom': 'skirt', 'shoes': 'sandals', 'accessory': 'sunglasses'}),
                ('Day Out', {'bottom': 'shorts', 'shoes': 'flats', 'accessory': 'tote'}),
            ]
        
        for theme_name, components in outfit_themes[:n]:
            outfit_items = [top_article]  # Start with the source top
            total_price = top_article.get('price', 0)
            
            # Find matching bottom
            bottom = self._find_outfit_component('bottom', components['bottom'], gender, style)
            if bottom:
                outfit_items.append(bottom)
                total_price += bottom.get('price', 0)
            
            # Find matching shoes
            shoes = self._find_outfit_component('shoes', components['shoes'], gender, style)
            if shoes:
                outfit_items.append(shoes)
                total_price += shoes.get('price', 0)
            
            # Find matching accessory
            accessory = self._find_outfit_component('accessory', components['accessory'], gender, style)
            if accessory:
                outfit_items.append(accessory)
                total_price += accessory.get('price', 0)
            
            if len(outfit_items) >= 3:  # At least 3 items to be a valid outfit
                outfits.append({
                    'outfit_name': theme_name,
                    'items': outfit_items,
                    'total_price': total_price,
                    'style': style  # Add style tag
                })
        
        return outfits
    
    def _build_outfits_from_bottom(self, bottom_article, gender, n=3):
        """Build complete outfits starting with a bottom - CONTEXT AWARE"""
        outfits = []
        style = self._detect_item_style(bottom_article)
        
        if style == 'formal':
            outfit_themes = [
                ('Business Formal', {'top': 'dress shirt', 'shoes': 'oxford shoes', 'accessory': 'belt'}),
                ('Corporate Style', {'top': 'shirt', 'shoes': 'dress shoes', 'accessory': 'watch'}),
            ] if gender == 'Men' else [
                ('Professional Elegance', {'top': 'blouse', 'shoes': 'heels', 'accessory': 'bag'}),
                ('Office Power', {'top': 'shirt', 'shoes': 'pumps', 'accessory': 'watch'}),
            ]
        elif style == 'sporty':
            outfit_themes = [
                ('Active Gear', {'top': 'sport shirt', 'shoes': 'trainers', 'accessory': 'cap'}),
                ('Gym Style', {'top': 't-shirt', 'shoes': 'running shoes', 'accessory': 'watch'}),
            ] if gender == 'Men' else [
                ('Fitness Fashion', {'top': 'sport top', 'shoes': 'trainers', 'accessory': 'bag'}),
                ('Active Chic', {'top': 'tank top', 'shoes': 'sneakers', 'accessory': 'headband'}),
            ]
        else:  # casual/elegant
            outfit_themes = [
                ('Classic Look', {'top': 'shirt', 'shoes': 'casual shoes', 'accessory': 'belt'}),
                ('Relaxed Style', {'top': 't-shirt', 'shoes': 'sneakers', 'accessory': 'watch'}),
            ] if gender == 'Men' else [
                ('Elegant Ensemble', {'top': 'blouse', 'shoes': 'heels', 'accessory': 'bag'}),
                ('Everyday Comfort', {'top': 't-shirt', 'shoes': 'sneakers', 'accessory': 'bag'}),
            ]
        
        for theme_name, components in outfit_themes[:n]:
            outfit_items = [bottom_article]
            total_price = bottom_article.get('price', 0)
            
            top = self._find_outfit_component('top', components['top'], gender, style)
            if top:
                outfit_items.append(top)
                total_price += top.get('price', 0)
            
            shoes = self._find_outfit_component('shoes', components['shoes'], gender, style)
            if shoes:
                outfit_items.append(shoes)
                total_price += shoes.get('price', 0)
            
            accessory = self._find_outfit_component('accessory', components['accessory'], gender, style)
            if accessory:
                outfit_items.append(accessory)
                total_price += accessory.get('price', 0)
            
            if len(outfit_items) >= 3:
                outfits.append({
                    'outfit_name': theme_name,
                    'items': outfit_items,
                    'total_price': total_price,
                    'style': style
                })
        
        return outfits
    
    def _build_outfits_from_shoes(self, shoes_article, gender, n=3):
        """Build complete outfits starting with shoes - CONTEXT AWARE"""
        outfits = []
        style = self._detect_item_style(shoes_article)
        
        if style == 'formal':
            outfit_themes = [
                ('Sharp & Polished', {'top': 'dress shirt', 'bottom': 'trousers', 'accessory': 'watch'}),
                ('Business Ready', {'top': 'shirt', 'bottom': 'suit trousers', 'accessory': 'tie'}),
            ] if gender == 'Men' else [
                ('Sophisticated', {'top': 'blouse', 'bottom': 'trousers', 'accessory': 'bag'}),
                ('Polished Professional', {'top': 'shirt', 'bottom': 'pencil skirt', 'accessory': 'jewellery'}),
            ]
        elif style == 'sporty':
            outfit_themes = [
                ('Athletic Ready', {'top': 'sport shirt', 'bottom': 'joggers', 'accessory': 'cap'}),
                ('Gym Outfit', {'top': 't-shirt', 'bottom': 'shorts', 'accessory': 'bag'}),
            ] if gender == 'Men' else [
                ('Workout Style', {'top': 'tank top', 'bottom': 'leggings', 'accessory': 'sports bag'}),
                ('Active Look', {'top': 'sport top', 'bottom': 'shorts', 'accessory': 'headband'}),
            ]
        else:  # casual
            outfit_themes = [
                ('Street Style', {'top': 't-shirt', 'bottom': 'jeans', 'accessory': 'cap'}),
                ('Casual Cool', {'top': 'polo', 'bottom': 'chinos', 'accessory': 'watch'}),
            ] if gender == 'Men' else [
                ('Urban Cool', {'top': 'top', 'bottom': 'jeans', 'accessory': 'bag'}),
                ('Everyday Chic', {'top': 't-shirt', 'bottom': 'skirt', 'accessory': 'sunglasses'}),
            ]
        
        for theme_name, components in outfit_themes[:n]:
            outfit_items = [shoes_article]
            total_price = shoes_article.get('price', 0)
            
            top = self._find_outfit_component('top', components['top'], gender, style)
            if top:
                outfit_items.append(top)
                total_price += top.get('price', 0)
            
            bottom = self._find_outfit_component('bottom', components['bottom'], gender, style)
            if bottom:
                outfit_items.append(bottom)
                total_price += bottom.get('price', 0)
            
            accessory = self._find_outfit_component('accessory', components['accessory'], gender, style)
            if accessory:
                outfit_items.append(accessory)
                total_price += accessory.get('price', 0)
            
            if len(outfit_items) >= 3:
                outfits.append({
                    'outfit_name': theme_name,
                    'items': outfit_items,
                    'total_price': total_price,
                    'style': style
                })
        
        return outfits
    
    def _build_outfits_from_dress(self, dress_article, gender, n=3):
        """Build complete outfits starting with a dress - CONTEXT AWARE"""
        outfits = []
        style = self._detect_item_style(dress_article)
        
        if style == 'elegant' or style == 'formal':
            outfit_themes = [
                ('Evening Elegance', {'shoes': 'heels', 'accessory': 'clutch'}),
                ('Cocktail Party', {'shoes': 'sandals', 'accessory': 'jewellery'}),
                ('Gala Ready', {'shoes': 'pumps', 'accessory': 'bag'}),
            ]
        else:  # casual
            outfit_themes = [
                ('Day Time Charm', {'shoes': 'sandals', 'accessory': 'sunglasses'}),
                ('Casual Elegance', {'shoes': 'flats', 'accessory': 'tote'}),
                ('Brunch Style', {'shoes': 'sneakers', 'accessory': 'bag'}),
            ]
        
        for theme_name, components in outfit_themes[:n]:
            outfit_items = [dress_article]
            total_price = dress_article.get('price', 0)
            
            shoes = self._find_outfit_component('shoes', components['shoes'], gender, style)
            if shoes:
                outfit_items.append(shoes)
                total_price += shoes.get('price', 0)
            
            accessory = self._find_outfit_component('accessory', components['accessory'], gender, style)
            if accessory:
                outfit_items.append(accessory)
                total_price += accessory.get('price', 0)
            
            if len(outfit_items) >= 2:
                outfits.append({
                    'outfit_name': theme_name,
                    'items': outfit_items,
                    'total_price': total_price,
                    'style': style
                })
        
        return outfits
    
    def _build_outfits_with_accessory(self, accessory_article, gender, n=3):
        """Build complete outfits that include this accessory - CONTEXT AWARE"""
        outfits = []
        style = self._detect_item_style(accessory_article)
        
        outfit_themes = [
            ('Complete Look', {'top': 'shirt', 'bottom': 'trousers', 'shoes': 'shoes'}),
        ]
        
        for theme_name, components in outfit_themes[:n]:
            outfit_items = [accessory_article]
            total_price = accessory_article.get('price', 0)
            
            top = self._find_outfit_component('top', components['top'], gender, style)
            if top:
                outfit_items.append(top)
                total_price += top.get('price', 0)
            
            bottom = self._find_outfit_component('bottom', components['bottom'], gender, style)
            if bottom:
                outfit_items.append(bottom)
                total_price += bottom.get('price', 0)
            
            shoes = self._find_outfit_component('shoes', components['shoes'], gender, style)
            if shoes:
                outfit_items.append(shoes)
                total_price += shoes.get('price', 0)
            
            if len(outfit_items) >= 3:
                outfits.append({
                    'outfit_name': theme_name,
                    'items': outfit_items,
                    'total_price': total_price,
                    'style': style
                })
        
        return outfits
    
    def _find_outfit_component(self, component_type, search_term, gender, style='casual'):
        """Find a specific component for an outfit - STYLE AWARE"""
        # Build search mask based on search term
        mask = self.articles_df['product_type_name'].str.contains(search_term, case=False, na=False)
        
        # Add style-specific filters
        if style == 'formal':
            # Prefer formal items
            formal_mask = (
                self.articles_df['prod_name'].str.contains('formal|business|office|suit|dress', case=False, na=False) |
                self.articles_df['section_name'].str.contains('formal|office', case=False, na=False)
            )
            mask = mask & formal_mask
        
        elif style == 'sporty':
            # Prefer sporty items
            sporty_mask = (
                self.articles_df['prod_name'].str.contains('sport|active|gym|running|training', case=False, na=False) |
                self.articles_df['section_name'].str.contains('sport|active', case=False, na=False)
            )
            mask = mask & sporty_mask
        
        elif style == 'elegant':
            # Prefer elegant items
            elegant_mask = (
                self.articles_df['prod_name'].str.contains('elegant|evening|party|cocktail|silk|satin', case=False, na=False) |
                self.articles_df['section_name'].str.contains('evening|party', case=False, na=False)
            )
            mask = mask & elegant_mask
        
        candidates = self.articles_df[mask].copy()
        
        # If style filtering was too strict and gave no results, fallback to general search
        if len(candidates) == 0:
            mask = self.articles_df['product_type_name'].str.contains(search_term, case=False, na=False)
            candidates = self.articles_df[mask].copy()
        
        # Filter by gender
        if gender:
            gender_mask = self._gender_mask(candidates, gender)
            filtered = candidates[gender_mask]
            if len(filtered) > 0:
                candidates = filtered
        
        if len(candidates) == 0:
            return None
        
        # Pick a random one
        article = candidates.sample(n=1).iloc[0].to_dict()
        if 'price' not in article or pd.isna(article.get('price')):
            article['price'] = self._generate_price(article)
        
        return article

    # ── Diagnostics ──────────────────────────────────────────────────────────
    def check_images_availability(self):
        self._ensure_loaded()
        total = len(self.articles_df)
        sample_size = min(1000, total)
        sample_ids = self.articles_df['article_id'].sample(sample_size).tolist()
        with_images = sum(1 for aid in sample_ids if self.get_article_image_path(aid))
        percentage = (with_images / sample_size) * 100
        print(f"Checked {sample_size} products: {with_images} have images ({percentage:.1f}%)")
        return percentage > 0