"""
Configuration for TD Realty Ohio SEO Blog Optimizer
"""

BUSINESS = {
    "name": "TD Realty Ohio, LLC",
    "url": "https://tdrealtyohio.com",
    "tagline": "Central Ohio's Discount Real Estate Brokerage",
    "services": [
        "1% listing commission (sell + buy combo)",
        "2% listing commission (sell only)",
        "1% cashback for first-time homebuyers",
        "Free pre-listing inspections",
    ],
    "communities": [
        "Westerville", "Dublin", "Powell", "Delaware", "Lewis Center",
        "Sunbury", "Galena", "Centerburg", "Johnstown", "New Albany",
        "Gahanna", "Reynoldsburg", "Pickerington", "Canal Winchester",
        "Grove City", "Hilliard", "Plain City",
    ],
    "phone": "(614) 300-1272",
    "founded": 2017,
}

SCORING = {
    "word_count": {
        "weight": 10,
        "target_min": 1500,
        "target_max": 2500,
        "hard_min": 800,
        "hard_max": 3500,
    },
    "keyword_optimization": {
        "weight": 15,
        "target_density_min": 0.008,
        "target_density_max": 0.02,
        "checks": [
            "keyword_in_title",
            "keyword_in_first_100_words",
            "keyword_in_headings",
            "keyword_density_in_range",
            "keyword_in_meta_description",
        ],
    },
    "heading_structure": {
        "weight": 10,
        "target_h2_count_min": 3,
        "target_h2_count_max": 8,
        "target_h3_count_min": 2,
    },
    "readability": {
        "weight": 10,
        "target_avg_sentence_length_min": 12,
        "target_avg_sentence_length_max": 22,
        "target_avg_paragraph_sentences_min": 2,
        "target_avg_paragraph_sentences_max": 5,
    },
    "local_seo": {
        "weight": 15,
        "community_mention_min": 3,
        "region_terms": [
            "Central Ohio", "Franklin County", "Delaware County",
            "Columbus", "Columbus metro", "I-270", "I-71",
            "Polaris", "Easton", "Short North",
        ],
    },
    "meta_description": {
        "weight": 10,
        "target_length_min": 140,
        "target_length_max": 160,
    },
    "internal_linking": {
        "weight": 10,
        "target_min_links": 3,
        "target_max_links": 8,
    },
    "content_depth": {
        "weight": 10,
        "target_unique_sections": 4,
        "bonus_features": [
            "statistics",
            "faq_section",
            "comparison_data",
            "market_data",
        ],
    },
    "call_to_action": {
        "weight": 5,
        "target_cta_count_min": 2,
        "target_cta_count_max": 4,
    },
    "frontmatter": {
        "weight": 5,
        "required_fields": [
            "title", "description", "date", "keywords",
            "author", "community", "category",
        ],
    },
}

ITERATIONS = {
    "default_count": 5,
    "max_count": 15,
    "improvement_threshold": 1.0,
    "plateau_patience": 2,
}

OUTPUT = {
    "dir": "output",
    "save_all_versions": True,
    "final_format": "markdown",
}

CONTENT_TYPES = {
    "market_update": {
        "description": "Monthly/quarterly real estate market update for a specific community",
        "target_keywords_pattern": "{community} real estate market {year}",
    },
    "community_guide": {
        "description": "Comprehensive guide to living in a specific community",
        "target_keywords_pattern": "living in {community} Ohio",
    },
    "home_buying": {
        "description": "Home buying guide focused on a specific community",
        "target_keywords_pattern": "homes for sale in {community} Ohio {year}",
    },
    "home_selling": {
        "description": "Home selling guide with discount brokerage angle",
        "target_keywords_pattern": "sell house {community} Ohio low commission",
    },
    "mortgage_rates": {
        "description": "Mortgage rate update with local context",
        "target_keywords_pattern": "mortgage rates {community} Ohio {year}",
    },
    "neighborhood": {
        "description": "Neighborhood spotlight or comparison",
        "target_keywords_pattern": "best neighborhoods {community} Ohio",
    },
    "homebuyer_programs": {
        "description": "Guide to Ohio first-time homebuyer programs, down payment assistance, and grants available in a specific community",
        "target_keywords_pattern": "first time home buyer programs {community} Ohio {year}",
    },
    "local_events": {
        "description": "Guide to local events, festivals, farmers markets, and community activities in a specific area",
        "target_keywords_pattern": "events and things to do in {community} Ohio {year}",
    },
    "local_history": {
        "description": "Historical facts, landmarks, and interesting locations in a specific community",
        "target_keywords_pattern": "history of {community} Ohio interesting facts",
    },
}
