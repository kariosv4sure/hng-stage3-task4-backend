"""
Natural Language Query Parser for Profile Search

Goals:
- Convert simple English queries into structured filters
- Be deterministic (same input always same output)
- Fail loudly on invalid or unrecognized queries
"""

import re
from typing import Dict, Any, Optional


# ---------------- COUNTRY MAP ----------------
COUNTRY_NAME_MAP = {
    "central african republic": "CF",
    "equatorial guinea": "GQ",
    "papua new guinea": "PG",
    "south africa": "ZA",
    "south sudan": "SS",
    "united kingdom": "GB",
    "united states": "US",
    "western sahara": "EH",
    "burkina faso": "BF",
    "cape verde": "CV",
    "costa rica": "CR",
    "cote d'ivoire": "CI",
    "côte d'ivoire": "CI",
    "dr congo": "CD",
    "congo": "CG",
    "el salvador": "SV",
    "guinea bissau": "GW",
    "ivory coast": "CI",
    "new zealand": "NZ",
    "north korea": "KP",
    "south korea": "KR",
    "saudi arabia": "SA",
    "sierra leone": "SL",
    "sri lanka": "LK",
    "vatican city": "VA",
    "algeria": "DZ",
    "angola": "AO",
    "australia": "AU",
    "benin": "BJ",
    "botswana": "BW",
    "brazil": "BR",
    "burundi": "BI",
    "cameroon": "CM",
    "canada": "CA",
    "chad": "TD",
    "china": "CN",
    "djibouti": "DJ",
    "egypt": "EG",
    "ethiopia": "ET",
    "france": "FR",
    "germany": "DE",
    "ghana": "GH",
    "india": "IN",
    "japan": "JP",
    "kenya": "KE",
    "liberia": "LR",
    "libya": "LY",
    "madagascar": "MG",
    "malawi": "MW",
    "mali": "ML",
    "morocco": "MA",
    "mozambique": "MZ",
    "namibia": "NA",
    "nigeria": "NG",
    "rwanda": "RW",
    "senegal": "SN",
    "somalia": "SO",
    "south africa": "ZA",
    "sudan": "SD",
    "tanzania": "TZ",
    "uganda": "UG",
    "zambia": "ZM",
    "zimbabwe": "ZW",
    "uk": "GB",
    "usa": "US",
    "uae": "AE"
}

# ---------------- KEYWORDS ----------------
MALE = {"male", "males", "man", "men", "boy", "boys"}
FEMALE = {"female", "females", "woman", "women", "girl", "girls"}

TEEN = {"teen", "teens", "teenager", "teenagers"}
ADULT = {"adult", "adults"}
SENIOR = {"senior", "seniors", "elderly"}
CHILD = {"child", "children", "kid", "kids"}


class NaturalLanguageParser:
    def __init__(self):
        self.filters: Dict[str, Any] = {}

    # ---------------- MAIN ENTRY ----------------
    def parse(self, query: str) -> Dict[str, Any]:
        if not query or not query.strip():
            raise ValueError("Empty query not allowed")

        q = query.lower().strip()
        self.filters = {}

        words = set(re.findall(r"\b\w+\b", q))

        self._gender(words)
        self._young(q)
        self._age(q)
        self._age_group(words)
        self._country(q)

        # conflict resolution
        if "age_group" in self.filters:
            self.filters.pop("min_age", None)
            self.filters.pop("max_age", None)

        # validation
        if "min_age" in self.filters and "max_age" in self.filters:
            if self.filters["min_age"] > self.filters["max_age"]:
                raise ValueError("Invalid age range")

        if not self.filters:
            raise ValueError("Unable to interpret query")

        return self.filters

    # ---------------- GENDER ----------------
    def _gender(self, words: set):
        if words & MALE:
            self.filters["gender"] = "male"
        elif words & FEMALE:
            self.filters["gender"] = "female"

    # ---------------- YOUNG ----------------
    def _young(self, q: str):
        if re.search(r"\byoung\b", q):
            self.filters["min_age"] = 16
            self.filters["max_age"] = 24

    # ---------------- AGE RULES ----------------
    def _age(self, q: str):
        # over / above
        over = re.search(r"(?:over|above|older than)\s+(\d+)", q)
        if over:
            self.filters["min_age"] = max(self.filters.get("min_age", 0), int(over.group(1)))

        # under / below
        under = re.search(r"(?:under|below|younger than)\s+(\d+)", q)
        if under:
            self.filters["max_age"] = min(self.filters.get("max_age", 200), int(under.group(1)))

    # ---------------- AGE GROUP ----------------
    def _age_group(self, words: set):
        if words & TEEN:
            self.filters["age_group"] = "teenager"
        elif words & CHILD:
            self.filters["age_group"] = "child"
        elif words & SENIOR:
            self.filters["age_group"] = "senior"
        elif words & ADULT:
            self.filters["age_group"] = "adult"

    # ---------------- COUNTRY ----------------
    def _country(self, q: str):
        # direct match first
        for name in sorted(COUNTRY_NAME_MAP.keys(), key=len, reverse=True):
            if name in q:
                self.filters["country_id"] = COUNTRY_NAME_MAP[name]
                return


# ---------------- PUBLIC API ----------------
def parse_query(query: str) -> Dict[str, Any]:
    return NaturalLanguageParser().parse(query)
