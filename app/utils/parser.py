"""
Natural Language Query Parser for Profile Search

Supported Keywords and Mappings:
- "young" → min_age=16, max_age=24 (word boundary matched)
- "males"/"male"/"men"/"man"/"boy" → gender=male
- "females"/"female"/"women"/"woman"/"girl" → gender=female
- "from [country]" → country_id (uses country name matching)
- "above [age]" / "over [age]" → min_age
- "below [age]" / "under [age]" → max_age
- "teenagers"/"teen"/"teens" → age_group=teenager
- "adults"/"adult" → age_group=adult
- "seniors"/"senior"/"elderly" → age_group=senior
- "children"/"child"/"kids" → age_group=child

Limitations:
- Does NOT support complex logic (AND/OR combinations)
- Does NOT support age ranges like "between 20 and 30"
- Does NOT support probability filters
- Age group takes precedence over numeric age ranges when both are present
- Invalid age ranges (min_age > max_age) will raise an error
- Only supports English queries
"""

import re
from typing import Dict, Any

# Country name to ISO code mapping (sorted by length for accurate matching)
COUNTRY_NAME_MAP = {
    "central african republic": "CF", "equatorial guinea": "GQ",
    "papua new guinea": "PG", "south africa": "ZA", "south sudan": "SS",
    "united kingdom": "GB", "united states": "US", "western sahara": "EH",
    "burkina faso": "BF", "cape verde": "CV", "costa rica": "CR",
    "côte d'ivoire": "CI", "cote d'ivoire": "CI", "dr congo": "CD",
    "el salvador": "SV", "guinea bissau": "GW", "guinea-bissau": "GW",
    "ivory coast": "CI", "new zealand": "NZ", "north korea": "KP",
    "puerto rico": "PR", "sao tome": "ST", "saudi arabia": "SA",
    "sierra leone": "SL", "south korea": "KR", "sri lanka": "LK",
    "timor leste": "TL", "vatican city": "VA",
    "algeria": "DZ", "angola": "AO", "australia": "AU", "benin": "BJ",
    "botswana": "BW", "brazil": "BR", "burundi": "BI", "cameroon": "CM",
    "canada": "CA", "chad": "TD", "china": "CN", "comoros": "KM",
    "congo": "CG", "djibouti": "DJ", "egypt": "EG", "eritrea": "ER",
    "eswatini": "SZ", "ethiopia": "ET", "france": "FR", "gabon": "GA",
    "gambia": "GM", "germany": "DE", "ghana": "GH", "guinea": "GN",
    "india": "IN", "japan": "JP", "kenya": "KE", "lesotho": "LS",
    "liberia": "LR", "libya": "LY", "madagascar": "MG", "malawi": "MW",
    "mali": "ML", "mauritania": "MR", "mauritius": "MU", "morocco": "MA",
    "mozambique": "MZ", "namibia": "NA", "niger": "NE", "nigeria": "NG",
    "rwanda": "RW", "senegal": "SN", "seychelles": "SC", "somalia": "SO",
    "sudan": "SD", "tanzania": "TZ", "togo": "TG", "tunisia": "TN",
    "uganda": "UG", "zambia": "ZM", "zimbabwe": "ZW",
    "usa": "US", "uk": "GB", "uae": "AE", "drc": "CD", "car": "CF"
}

# Gender keywords
MALE_KEYWORDS = {"male", "males", "man", "men", "boy", "boys", "guy", "guys"}
FEMALE_KEYWORDS = {"female", "females", "woman", "women", "girl", "girls", "lady", "ladies"}

# Age group keywords
TEENAGER_KEYWORDS = {"teenager", "teenagers", "teen", "teens", "adolescent", "adolescents"}
ADULT_KEYWORDS = {"adult", "adults"}
SENIOR_KEYWORDS = {"senior", "seniors", "elderly", "old", "older"}
CHILD_KEYWORDS = {"child", "children", "kid", "kids"}


class NaturalLanguageParser:
    """Rule-based natural language query parser for profile search."""
    
    def __init__(self):
        self.filters: Dict[str, Any] = {}
    
    def parse(self, query: str) -> Dict[str, Any]:
        """
        Parse a natural language query into filters.
        
        Args:
            query: Natural language query string (e.g., "young males from nigeria")
            
        Returns:
            Dictionary of filters (gender, country_id, min_age, max_age, age_group)
            
        Raises:
            ValueError: If query cannot be interpreted or has invalid age range
        """
        if not query or not query.strip():
            raise ValueError("Unable to interpret query")
        
        query_lower = query.lower().strip()
        self.filters = {}
        
        # Extract clean tokens (handles punctuation)
        words = set(re.findall(r'\b\w+\b', query_lower))
        
        # Parse gender
        self._parse_gender(words)
        
        # Parse "young" keyword (word boundary match)
        self._parse_young(query_lower)
        
        # Parse age numbers (above/below/over/under)
        self._parse_age_numbers(query_lower)
        
        # Parse age groups (this overrides numeric age ranges)
        self._parse_age_groups(words)
        
        # Parse country (sorted by length for accurate matching)
        self._parse_country(query_lower)
        
        # Resolve conflicts: age_group takes precedence over numeric ranges
        if "age_group" in self.filters:
            self.filters.pop("min_age", None)
            self.filters.pop("max_age", None)
        
        # Validate age range (min_age must be <= max_age)
        if "min_age" in self.filters and "max_age" in self.filters:
            if self.filters["min_age"] > self.filters["max_age"]:
                raise ValueError("Invalid age range")
        
        # If no filters were extracted, the query couldn't be interpreted
        if not self.filters:
            raise ValueError("Unable to interpret query")
        
        return self.filters
    
    def _parse_gender(self, words: set) -> None:
        """Extract gender from query tokens."""
        if words & MALE_KEYWORDS:
            self.filters["gender"] = "male"
        elif words & FEMALE_KEYWORDS:
            self.filters["gender"] = "female"
    
    def _parse_young(self, query: str) -> None:
        """Map 'young' to age range 16-24 (word boundary match)."""
        if re.search(r'\byoung\b', query):
            self.filters["min_age"] = 16
            self.filters["max_age"] = 24
    
    def _parse_age_numbers(self, query: str) -> None:
        """Extract age thresholds from phrases like 'above 30' or 'under 25'."""
        # Match patterns like "above 30", "over 25", "older than 40"
        above_pattern = r'(?:above|over|older\s+than|>\s*)\s*(\d+)'
        above_match = re.search(above_pattern, query)
        if above_match:
            age = int(above_match.group(1))
            self.filters["min_age"] = max(self.filters.get("min_age", 0), age)
        
        # Match patterns like "below 20", "under 18", "younger than 30"
        below_pattern = r'(?:below|under|younger\s+than|<\s*)\s*(\d+)'
        below_match = re.search(below_pattern, query)
        if below_match:
            age = int(below_match.group(1))
            current_max = self.filters.get("max_age", 200)
            self.filters["max_age"] = min(current_max, age)
    
    def _parse_age_groups(self, words: set) -> None:
        """Extract age group from query tokens."""
        if words & TEENAGER_KEYWORDS:
            self.filters["age_group"] = "teenager"
        elif words & ADULT_KEYWORDS:
            self.filters["age_group"] = "adult"
        elif words & SENIOR_KEYWORDS:
            self.filters["age_group"] = "senior"
        elif words & CHILD_KEYWORDS:
            self.filters["age_group"] = "child"
    
    def _parse_country(self, query: str) -> None:
        """Extract country from query using phrase matching."""
        # Check for "from [country]" pattern (stops at keywords like above/below/over/under)
        from_pattern = r'from\s+([a-z\s\'-]+?)(?:\s+(?:above|below|over|under|and)|$)'
        from_match = re.search(from_pattern, query)
        
        if from_match:
            country_phrase = from_match.group(1).strip()
        else:
            # Check for "in [country]" pattern
            in_pattern = r'in\s+([a-z\s\'-]+?)(?:\s+(?:above|below|over|under|and)|$)'
            in_match = re.search(in_pattern, query)
            if in_match:
                country_phrase = in_match.group(1).strip()
            else:
                country_phrase = None
        
        # Try exact match first
        if country_phrase and country_phrase in COUNTRY_NAME_MAP:
            self.filters["country_id"] = COUNTRY_NAME_MAP[country_phrase]
            return
        
        # Try to find any country name in the query (longest first)
        for country_name in sorted(COUNTRY_NAME_MAP, key=len, reverse=True):
            if country_name in query:
                self.filters["country_id"] = COUNTRY_NAME_MAP[country_name]
                return


def parse_query(query: str) -> Dict[str, Any]:
    """
    Convenience function to parse a natural language query.
    
    Args:
        query: Natural language query string
        
    Returns:
        Dictionary of filters
        
    Raises:
        ValueError: If query cannot be interpreted or has invalid age range
    """
    parser = NaturalLanguageParser()
    return parser.parse(query)

