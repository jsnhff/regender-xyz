"""Character context creation for transformation phase."""

from typing import Dict, Any, Optional


def create_character_context(characters: Dict[str, Any]) -> str:
    """Create a character context string for transformations.
    
    Args:
        characters: Dictionary of character data
        
    Returns:
        Formatted string with character information
    """
    if not characters:
        return ""
    
    context_parts = ["Known characters:"]
    for name, info in characters.items():
        gender = info.get('gender', 'unknown')
        context_parts.append(f"- {name}: {gender}")
    
    return '\n'.join(context_parts)


def create_character_mapping(characters: Dict[str, Any], 
                           transform_type: str) -> Dict[str, Dict[str, str]]:
    """Create a character mapping for gender transformation.
    
    Args:
        characters: Dictionary of character data
        transform_type: Type of transformation (all_female/all_male/gender_swap)
        
    Returns:
        Dictionary mapping original names to transformed versions
    """
    mapping = {}
    
    for name, info in characters.items():
        original_gender = info.get('gender', 'unknown')
        
        # Determine target gender based on transform type
        if transform_type == 'all_female':
            if original_gender == 'male':
                mapping[name] = {
                    'new_name': _feminize_name(name),
                    'original_gender': 'male',
                    'new_gender': 'female'
                }
        elif transform_type == 'all_male':
            if original_gender == 'female':
                mapping[name] = {
                    'new_name': _masculinize_name(name),
                    'original_gender': 'female',
                    'new_gender': 'male'
                }
        elif transform_type == 'gender_swap':
            if original_gender == 'male':
                mapping[name] = {
                    'new_name': _feminize_name(name),
                    'original_gender': 'male',
                    'new_gender': 'female'
                }
            elif original_gender == 'female':
                mapping[name] = {
                    'new_name': _masculinize_name(name),
                    'original_gender': 'female',
                    'new_gender': 'male'
                }
    
    return mapping


def create_all_female_mapping(characters: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Create a mapping where all characters become female.
    
    Args:
        characters: Dictionary of character data
        
    Returns:
        Dictionary mapping original names to female versions
    """
    mapping = {}
    
    for name, info in characters.items():
        original_gender = info.get('gender', 'unknown')
        
        if original_gender == 'male':
            mapping[name] = {
                'new_name': _feminize_name(name),
                'original_gender': 'male',
                'new_gender': 'female'
            }
        else:
            # Keep female and unknown characters as-is
            mapping[name] = {
                'new_name': name,
                'original_gender': original_gender,
                'new_gender': original_gender
            }
    
    return mapping


def _feminize_name(name: str) -> str:
    """Convert a male name to a female equivalent.
    
    This is a simple implementation. In practice, you might want
    to use a more sophisticated name mapping or allow user customization.
    """
    # Common male to female name mappings
    name_map = {
        # Harry Potter specific
        'Harry': 'Harriet',
        'Harry Potter': 'Harriet Potter',
        'Ron': 'Veronica',
        'Ron Weasley': 'Veronica Weasley',
        'Ronald': 'Veronica',
        'Ronald Weasley': 'Veronica Weasley',
        'Albus': 'Alba',
        'Albus Dumbledore': 'Alba Dumbledore',
        'Severus': 'Severa',
        'Severus Snape': 'Severa Snape',
        'Draco': 'Dracona',
        'Draco Malfoy': 'Dracona Malfoy',
        'Neville': 'Nevilla',
        'Neville Longbottom': 'Nevilla Longbottom',
        'Sirius': 'Siria',
        'Sirius Black': 'Siria Black',
        'Remus': 'Rema',
        'Remus Lupin': 'Rema Lupin',
        'Fred': 'Freda',
        'George': 'Georgia',
        'Percy': 'Persephone',
        'Arthur': 'Artemis',
        'Vernon': 'Veronica',
        'Dudley': 'Dolly',
        
        # Common names
        'John': 'Joan',
        'James': 'Jamie',
        'Robert': 'Roberta',
        'Michael': 'Michelle',
        'William': 'Willow',
        'David': 'Diana',
        'Richard': 'Rachel',
        'Joseph': 'Josephine',
        'Charles': 'Charlotte',
        'Thomas': 'Tamara',
        'Daniel': 'Danielle',
        'Paul': 'Paula',
        'Mark': 'Mary',
        'George': 'Georgia',
        'Steven': 'Stephanie',
        'Andrew': 'Andrea',
        'Kenneth': 'Kendra',
        'Joshua': 'Jessica',
        'Kevin': 'Karen',
        'Brian': 'Brianna',
        'Edward': 'Edwina',
        'Peter': 'Petra',
        'Christopher': 'Christina',
        'Matthew': 'Martha',
        'Anthony': 'Antonia',
        'Donald': 'Donna',
        
        # Titles
        'Mr.': 'Ms.',
        'Master': 'Miss',
        'Lord': 'Lady',
        'Sir': 'Dame',
        'King': 'Queen',
        'Prince': 'Princess',
        'Duke': 'Duchess',
        'Earl': 'Countess',
        'Baron': 'Baroness'
    }
    
    # Check full name first
    if name in name_map:
        return name_map[name]
    
    # Check first name
    parts = name.split()
    if parts[0] in name_map:
        parts[0] = name_map[parts[0]]
        return ' '.join(parts)
    
    # Default: add 'a' to the end if it doesn't already end with a feminine suffix
    if not name.endswith(('a', 'e', 'y', 'ie', 'ine', 'elle', 'ette')):
        return name + 'a'
    
    return name


def _masculinize_name(name: str) -> str:
    """Convert a female name to a male equivalent."""
    # Common female to male name mappings
    name_map = {
        # Harry Potter specific
        'Hermione': 'Herman',
        'Hermione Granger': 'Herman Granger',
        'Minerva': 'Marvin',
        'Minerva McGonagall': 'Marvin McGonagall',
        'Luna': 'Lucius',
        'Luna Lovegood': 'Lucius Lovegood',
        'Ginny': 'George',
        'Ginny Weasley': 'George Weasley',
        'Molly': 'Morris',
        'Molly Weasley': 'Morris Weasley',
        'Bellatrix': 'Bellator',
        'Narcissa': 'Narcissus',
        'Petunia': 'Peter',
        
        # Common names
        'Mary': 'Mark',
        'Patricia': 'Patrick',
        'Linda': 'Leonard',
        'Barbara': 'Barry',
        'Elizabeth': 'Elijah',
        'Jennifer': 'Geoffrey',
        'Maria': 'Mario',
        'Susan': 'Steven',
        'Margaret': 'Marcus',
        'Dorothy': 'Donald',
        'Lisa': 'Louis',
        'Nancy': 'Nathan',
        'Karen': 'Kevin',
        'Betty': 'Brett',
        'Helen': 'Henry',
        'Sandra': 'Samuel',
        'Donna': 'Donald',
        'Carol': 'Carl',
        'Ruth': 'Russell',
        'Sharon': 'Shawn',
        'Michelle': 'Michael',
        'Laura': 'Lawrence',
        'Sarah': 'Samuel',
        'Kimberly': 'Kenneth',
        'Deborah': 'David',
        
        # Titles
        'Ms.': 'Mr.',
        'Mrs.': 'Mr.',
        'Miss': 'Master',
        'Lady': 'Lord',
        'Dame': 'Sir',
        'Queen': 'King',
        'Princess': 'Prince',
        'Duchess': 'Duke',
        'Countess': 'Earl',
        'Baroness': 'Baron'
    }
    
    # Check full name first
    if name in name_map:
        return name_map[name]
    
    # Check first name
    parts = name.split()
    if parts[0] in name_map:
        parts[0] = name_map[parts[0]]
        return ' '.join(parts)
    
    # Default: remove feminine suffixes
    if name.endswith('a') and len(name) > 3:
        return name[:-1]
    elif name.endswith('ine'):
        return name[:-3]
    elif name.endswith('elle'):
        return name[:-4]
    
    return name


def _neutralize_name(name: str) -> str:
    """Convert a name to a gender-neutral version."""
    # For now, just return the name as-is
    # In a real implementation, you might map to truly neutral names
    # or use initials, last names only, etc.
    return name