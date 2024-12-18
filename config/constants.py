"""Constants used throughout the application."""

GENDER_CATEGORIES = {
    'M': {
        'label': 'Male',
        'terms': ['male', 'man', 'boy', 'gentleman', 'father', 'son', 'mr', 'sir', 'he', 'his'],
        'pronouns': ['he', 'him', 'his']
    },
    'F': {
        'label': 'Female',
        'terms': ['female', 'woman', 'girl', 'lady', 'mother', 'daughter', 'ms', 'mrs', 'miss', 'she', 'her'],
        'pronouns': ['she', 'her', 'hers']
    },
    'NB': {
        'label': 'Non-binary',
        'terms': ['non-binary', 'nonbinary', 'enby', 'neutral', 'they'],
        'pronouns': ['they', 'them', 'theirs']
    },
    'UNK': {
        'label': 'Unknown',
        'terms': ['unknown', 'unspecified'],
        'pronouns': ['they', 'them', 'theirs']
    }
}

# File paths
DEFAULT_LOG_DIR = "logs"
CHARACTER_DATA_FILE = "character_roles_genders.json"

# API settings
MAX_RETRIES = 3
RETRY_DELAY = 5
DEFAULT_CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200