# queries.py - Fixed Version with Exact Matching and Proper Conditional Logic
import re
from sentence_transformers import SentenceTransformer, util
from typing import Dict, List, Tuple, Optional

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# ============================================================================
# FIXED QUERY PARSER - EXACT MATCHING & CONDITIONAL STATE LOGIC
# ============================================================================

class DynamicQueryParser:
    def __init__(self):
        self.specialties = {
            "cardiology": "Cardiology", "cardiologist": "Cardiology", "cardiologists": "Cardiology",
            "urology": "Urology", "urologist": "Urology", "urologists": "Urology",
            "oncology": "Oncology", "oncologist": "Oncology", "oncologists": "Oncology",
            "radiology": "Radiology", "radiologist": "Radiology", "radiologists": "Radiology",
            "neurology": "Neurology", "neurologist": "Neurology", "neurologists": "Neurology",
            "internal medicine": "Internal Medicine", "family medicine": "Family Medicine",
            "pediatrics": "Pediatrics", "psychiatry": "Psychiatry", "surgery": "Surgery",
            "emergency medicine": "Emergency Medicine", "anesthesiology": "Anesthesiology",
            "dermatology": "Dermatology", "orthopedics": "Orthopedic Surgery", "pulmonology": "Pulmonology"
        }
        
        self.states = {
            "california": "CA", "ca": "CA", "new york": "NY", "ny": "NY", 
            "texas": "TX", "tx": "TX", "florida": "FL", "fl": "FL",
            "illinois": "IL", "il": "IL", "pennsylvania": "PA", "pa": "PA",
            "ohio": "OH", "oh": "OH", "georgia": "GA", "ga": "GA",
            "north carolina": "NC", "nc": "NC", "michigan": "MI", "mi": "MI"
        }
        
        # EXACT city names as they appear in the database (case-sensitive)
        self.exact_cities = {
            "san francisco": "SAN FRANCISCO",
            "brooklyn": "Brooklyn", 
            "buffalo": "Buffalo",
            "oakland": "Oakland",
            "queens": "Queens", 
            "syracuse": "Syracuse",
            "santa ana": "Santa Ana",
            "fresno": "Fresno",
            "new york": "New York",
            "los angeles": "Los Angeles",
            "chicago": "Chicago"
        }

    def preprocess_query(self, text: str) -> str:
        """Preprocess query to handle variations"""
        # Normalize common variations
        text = re.sub(r'\bpracticing from\b', 'practicing for', text)
        text = re.sub(r'\bwith experience of\b', 'with', text)
        return text

    def extract_city(self, text: str) -> Optional[str]:
        """Extract city name from text - FIXED for exact matching"""
        text_lower = text.lower()
        
        # Remove the years portion to avoid interference
        years_pattern = r'(?:practicing|with|having|experience).?(?:more than|less than|over|under|exactly|between).?\d+\s*years?'
        text_without_years = re.sub(years_pattern, '', text_lower)
        
        # More specific patterns for city extraction
        city_patterns = [
            r'\bin\s+city\s+named\s+([a-z\s]+?)(?:\s+and|\s*$)',
            r'\bcity\s+named\s+([a-z\s]+?)(?:\s+and|\s*$)',
            r'\bin\s+([a-z\s]+?)(?:\s+and|\s+practicing|\s+with|\s*$)',
            r'\bfrom\s+([a-z\s]+?)(?:\s+and|\s+practicing|\s+with|\s*$)',
            r'\blocated\s+in\s+([a-z\s]+?)(?:\s+and|\s*$)'
        ]
        
        for pattern in city_patterns:
            match = re.search(pattern, text_without_years)
            if match:
                potential_city = match.group(1).strip()
                # Clean up common words
                potential_city = re.sub(r'\b(city|state|county|and|with|practicing)\b', '', potential_city).strip()
                
                # Check against exact known cities
                if potential_city in self.exact_cities:
                    return self.exact_cities[potential_city]  # Return exact database spelling
        
        # Fallback: Check if any known city is mentioned directly
        for city_lower, city_exact in self.exact_cities.items():
            if city_lower in text_lower:
                return city_exact  # Return exact database spelling
        
        return None

    def extract_state(self, text: str) -> Optional[str]:
        """Extract state from text - ONLY if explicitly mentioned"""
        text_lower = text.lower()
        
        # Remove years portion first
        years_pattern = r'(?:practicing|with|having|experience).?(?:more than|less than|over|under|exactly|between).?\d+\s*years?'
        text_without_years = re.sub(years_pattern, '', text_lower)
        
        # Only look for explicit state mentions
        state_patterns = [
            r'\bin\s+([a-z\s]+?)(?:\s+state)?\s+(?:and|with|$)',  # "in California", "in CA state"
            r'\bstate\s+of\s+([a-z\s]+?)(?:\s+and|with|$)',      # "state of California"  
            r'\b([a-z]{2})\b'  # Two letter state codes
        ]
        
        for pattern in state_patterns:
            matches = re.findall(pattern, text_without_years)
            for match in matches:
                match = match.strip()
                if match in self.states:
                    return self.states[match]
        
        return None

    def extract_specialty(self, text: str) -> Optional[str]:
        """Extract medical specialty from text"""
        text_lower = text.lower()
        
        for specialty_key, specialty_value in self.specialties.items():
            if specialty_key in text_lower:
                return specialty_value
        return None

    def extract_years_condition(self, text: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract years in practice condition"""
        text_lower = text.lower()
        
        # Comprehensive patterns for years
        patterns = [
            # More than patterns
            (r'more\s+than\s+(\d+)\s*years?', '>', 1),
            (r'practicing\s+(?:from|for)\s+more\s+than\s+(\d+)\s*years?', '>', 1),
            (r'with\s+more\s+than\s+(\d+)\s*years?', '>', 1),
            (r'over\s+(\d+)\s*years?', '>', 1),
            (r'greater\s+than\s+(\d+)\s*years?', '>', 1),
            (r'above\s+(\d+)\s*years?', '>', 1),
            (r'>\s*(\d+)\s*years?', '>', 1),
            
            # Less than patterns
            (r'less\s+than\s+(\d+)\s*years?', '<', 1),
            (r'under\s+(\d+)\s*years?', '<', 1),
            (r'below\s+(\d+)\s*years?', '<', 1),
            (r'fewer\s+than\s+(\d+)\s*years?', '<', 1),
            (r'<\s*(\d+)\s*years?', '<', 1),
            
            # Exactly patterns
            (r'exactly\s+(\d+)\s*years?', '=', 1),
            (r'equal\s+to\s+(\d+)\s*years?', '=', 1),
            (r'(\d+)\s*years?\s+exactly', '=', 1),
            (r'=\s*(\d+)\s*years?', '=', 1),
            
            # Between patterns
            (r'between\s+(\d+)\s+and\s+(\d+)\s*years?', 'BETWEEN', 2),
            (r'(\d+)\s*-\s*(\d+)\s*years?', 'BETWEEN', 2)
        ]
        
        for pattern, operator, num_groups in patterns:
            match = re.search(pattern, text_lower)
            if match:
                if num_groups == 1:
                    return operator, int(match.group(1))
                elif num_groups == 2:
                    return f"BETWEEN {match.group(1)} AND {match.group(2)}", None
        
        return None, None

    def detect_query_type(self, text: str) -> str:
        """Detect if it's a count or list query"""
        text_lower = text.lower()
        
        count_indicators = ['how many', 'count', 'number of', 'total', 'amount']
        
        for indicator in count_indicators:
            if indicator in text_lower:
                return 'count'
        
        return 'list'

    def extract_validation_context(self, text: str) -> Optional[str]:
        """Extract validation-related context"""
        text_lower = text.lower()
        
        if 'expired' in text_lower and 'license' in text_lower:
            return 'expired_licenses'
        elif 'validation' in text_lower or 'error' in text_lower:
            if 'npi' in text_lower:
                return 'npi_validation_error'
            elif 'phone' in text_lower:
                return 'phone_validation_error'
            else:
                return 'general_validation_error'
        elif 'missing' in text_lower:
            if 'phone' in text_lower:
                return 'missing_phone'
            elif 'npi' in text_lower:
                return 'missing_npi'
            else:
                return 'missing_general'
        
        return None

    def build_sql_query(self, text: str) -> str:
        """Build SQL query from parsed components - FIXED"""
        # Preprocess the query
        text = self.preprocess_query(text)
        
        query_type = self.detect_query_type(text)
        
        # Extract all components
        years_op, years_val = self.extract_years_condition(text)
        city = self.extract_city(text)
        state = self.extract_state(text)
        specialty = self.extract_specialty(text)
        validation_context = self.extract_validation_context(text)
        
        # Build conditions - ONLY add what's actually found
        conditions = []
        
        # FIXED: Use exact city name matching without LOWER()
        if city:
            conditions.append(f"practice_city = '{city}'")
        
        # FIXED: Only add state condition if actually found in query
        if state:
            conditions.append(f"practice_state = '{state}'")
            
        if specialty:
            conditions.append(f"primary_specialty = '{specialty}'")
            
        if years_op and years_val is not None:
            conditions.append(f"years_in_practice {years_op} {years_val}")
        elif years_op and 'BETWEEN' in years_op:
            conditions.append(f"years_in_practice {years_op}")
        
        # Handle board certification
        text_lower = text.lower()
        if 'board certified' in text_lower or 'board-certified' in text_lower:
            if 'not board certified' in text_lower or 'not board-certified' in text_lower:
                conditions.append("board_certified = 'False'")
            else:
                conditions.append("board_certified = 'True'")
        
        # Handle accepting patients
        if 'accepting' in text_lower and 'patient' in text_lower:
            if 'not accepting' in text_lower:
                conditions.append("accepting_new_patients = 'No'")
            else:
                conditions.append("accepting_new_patients = 'Yes'")
        
        # Handle validation contexts
        if validation_context == 'expired_licenses':
            conditions.append("license_expiration_check = 'EXPIRED'")
        elif validation_context == 'npi_validation_error':
            conditions.append("npi_check != 'correct'")
        elif validation_context == 'phone_validation_error':
            conditions.append("practice_phone_check != 'correct'")
        elif validation_context == 'general_validation_error':
            conditions.append("(npi_check != 'correct' OR full_name_check != 'correct')")
        elif validation_context == 'missing_phone':
            conditions.append("(practice_phone IS NULL OR practice_phone = '')")
        elif validation_context == 'missing_npi':
            conditions.append("(npi IS NULL OR npi = '')")
        
        # Build final query
        if query_type == 'count':
            if conditions:
                where_clause = " AND ".join(conditions)
                return f"SELECT COUNT(*) as count FROM roster WHERE {where_clause}"
            else:
                return "SELECT COUNT(*) as total_count FROM roster"
        else:  # list query
            if conditions:
                where_clause = " AND ".join(conditions)
                return f"SELECT * FROM roster WHERE {where_clause} LIMIT 50"
            else:
                return "SELECT * FROM roster LIMIT 50"

# ============================================================================
# FALLBACK TEMPLATES FOR SIMPLE QUERIES
# ============================================================================

SIMPLE_TEMPLATES = {
    "all providers": "SELECT * FROM roster LIMIT 50",
    "total providers": "SELECT COUNT(*) as count FROM roster",
    "expired licenses": "SELECT * FROM roster WHERE license_expiration_check = 'EXPIRED' LIMIT 50",
    "board certified providers": "SELECT * FROM roster WHERE board_certified = 'True' LIMIT 50",
    "validation errors": "SELECT * FROM roster WHERE npi_check != 'correct' OR full_name_check != 'correct' LIMIT 50",
    "missing phone numbers": "SELECT * FROM roster WHERE practice_phone IS NULL OR practice_phone = '' LIMIT 50",
    "cardiologists": "SELECT * FROM roster WHERE primary_specialty = 'Cardiology' LIMIT 50",
    "providers in california": "SELECT * FROM roster WHERE practice_state = 'CA' LIMIT 50",
    "providers in new york": "SELECT * FROM roster WHERE practice_state = 'NY' LIMIT 50",
    # Add count-specific templates
    "how many providers": "SELECT COUNT(*) as count FROM roster",
    "count providers": "SELECT COUNT(*) as count FROM roster",
    "number of providers": "SELECT COUNT(*) as count FROM roster",
    "how many cardiologists": "SELECT COUNT(*) as count FROM roster WHERE primary_specialty = 'Cardiology'",
    "count cardiologists": "SELECT COUNT(*) as count FROM roster WHERE primary_specialty = 'Cardiology'",
}

# Create embeddings for simple templates
template_embeddings = {k: model.encode(k, convert_to_tensor=True) for k in SIMPLE_TEMPLATES}

# Create parser instance
parser = DynamicQueryParser()

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def parse_query(natural_language_query: str) -> str:
    """
    Parse natural language query and return SQL.
    
    FIXED Examples:
    "How many are practicing in city named San Francisco and practicing from more than 20 years"
    -> "SELECT COUNT(*) as count FROM roster WHERE practice_city = 'SAN FRANCISCO' AND years_in_practice > 20"
    
    "Show cardiologists with more than 15 years experience"  
    -> "SELECT * FROM roster WHERE primary_specialty = 'Cardiology' AND years_in_practice > 15 LIMIT 50"
    
    "List providers in California" (ONLY adds state if mentioned)
    -> "SELECT * FROM roster WHERE practice_state = 'CA' LIMIT 50"
    """
    
    try:
        # Use dynamic parsing
        dynamic_sql = parser.build_sql_query(natural_language_query)
        
        # Check if dynamic parsing found meaningful conditions
        if "WHERE" in dynamic_sql:
            return dynamic_sql
        
        # Fallback to template matching for very simple queries
        query_embedding = model.encode(natural_language_query, convert_to_tensor=True)
        
        best_template = max(
            template_embeddings.keys(),
            key=lambda k: util.cos_sim(query_embedding, template_embeddings[k])
        )
        
        return SIMPLE_TEMPLATES[best_template]
        
    except Exception as e:
        # Ultimate fallback
        return "SELECT * FROM roster LIMIT 50"

# ============================================================================
# TEST CASES (for debugging)
# ============================================================================

if __name__ == "_main_":
    test_queries = [
        "How many are practicing in city named San Francisco and practicing from more than 20 years",
        "Show all cardiologists with more than 15 years experience",  # No state mentioned
        "List board certified providers in New York with less than 5 years",
        "Count providers in Chicago accepting new patients",  # No state mentioned
        "How many urologists are there in Texas with between 10 and 20 years experience",
        "Show cardiologists",  # No city or state mentioned
        "List providers in Brooklyn"  # Only city, no state
    ]
    
    for query in test_queries:
        sql = parse_query(query)
        print(f"Query: {query}")
        print(f"SQL: {sql}")
        print("-" * 80)