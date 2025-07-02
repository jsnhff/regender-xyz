"""Create explicit character transformation context for different modes."""

from typing import Dict, Any

# Common name transformations
MALE_TO_FEMALE = {
    "John": "Jane",
    "William": "Willow", 
    "James": "Jamie",
    "Robert": "Roberta",
    "Michael": "Michelle",
    "David": "Davina",
    "Richard": "Rachel",
    "Joseph": "Josephine",
    "Charles": "Charlotte",
    "Thomas": "Tamara",
    "Christopher": "Christina",
    "Daniel": "Danielle",
    "Matthew": "Matilda",
    "George": "Georgia",
    "Edward": "Edwina",
    "Andrew": "Andrea",
    "Paul": "Paula",
    "Mark": "Margaret",
    "Peter": "Petra",
    "Brian": "Brianna",
    "Kevin": "Karen",
    "Jason": "Jessica",
    "Frank": "Frances",
    "Henry": "Henrietta",
    "Gary": "Grace",
    "Nicholas": "Nicole",
    "Eric": "Erica",
    "Stephen": "Stephanie",
    "Philip": "Philippa",
    "Harry": "Harriet",
}

FEMALE_TO_MALE = {
    "Elizabeth": "Elliot",
    "Jane": "John",
    "Mary": "Mark",
    "Catherine": "Christopher",
    "Kitty": "Kit",
    "Lydia": "Laurence",
    "Anne": "Andrew",
    "Susan": "Steven",
    "Margaret": "Martin",
    "Helen": "Henry",
    "Patricia": "Patrick",
    "Barbara": "Bernard",
    "Jennifer": "Jeremy",
    "Maria": "Marcus",
    "Nancy": "Nathan",
    "Karen": "Kevin",
    "Betty": "Brett",
    "Dorothy": "Donald",
    "Lisa": "Louis",
    "Sandra": "Samuel",
    "Ashley": "Ashton",
    "Kimberly": "Kenneth",
    "Donna": "Donald",
    "Carol": "Carl",
    "Michelle": "Michael",
    "Jessica": "Jason",
    "Sarah": "Samuel",
    "Rebecca": "Robert",
    "Laura": "Lawrence",
    "Emma": "Emmett",
}


def get_name_transformation(name: str, to_gender: str) -> str:
    """Get the transformed version of a name for the target gender."""
    if to_gender == "male":
        # Check if it's a known female name
        return FEMALE_TO_MALE.get(name, name)
    elif to_gender == "female":
        # Check if it's a known male name
        return MALE_TO_FEMALE.get(name, name)
    return name


def create_transformation_context(characters: Dict[str, Any], transform_mode: str) -> str:
    """
    Create explicit character transformation instructions based on mode.
    
    Args:
        characters: Dictionary of character information
        transform_mode: One of 'all_male', 'all_female', 'gender_swap'
        
    Returns:
        String with explicit transformation instructions
    """
    if not characters:
        return ""
    
    instructions = []
    
    if transform_mode == "all_male":
        instructions.append("CHARACTER TRANSFORMATIONS - ALL CHARACTERS MUST BE MALE:")
        instructions.append("")
        
        for name, info in characters.items():
            gender = info.get('gender', 'unknown')
            if gender == 'female':
                new_name = get_name_transformation(name, 'male')
                if new_name != name:
                    instructions.append(f"- {name} → {new_name} (MAKE MALE)")
                else:
                    instructions.append(f"- {name} → {name} (MAKE MALE - change pronouns to he/him/his)")
            else:
                instructions.append(f"- {name} (KEEP MALE)")
                
    elif transform_mode == "all_female":
        instructions.append("CHARACTER TRANSFORMATIONS - ALL CHARACTERS MUST BE FEMALE:")
        instructions.append("")
        
        for name, info in characters.items():
            gender = info.get('gender', 'unknown')
            if gender == 'male':
                new_name = get_name_transformation(name, 'female')
                if new_name != name:
                    instructions.append(f"- {name} → {new_name} (MAKE FEMALE)")
                else:
                    instructions.append(f"- {name} → {name} (MAKE FEMALE - change pronouns to she/her/her)")
            else:
                instructions.append(f"- {name} (KEEP FEMALE)")
                
    elif transform_mode == "gender_swap":
        instructions.append("CHARACTER TRANSFORMATIONS - SWAP EVERY CHARACTER'S GENDER:")
        instructions.append("")
        
        for name, info in characters.items():
            gender = info.get('gender', 'unknown')
            if gender == 'male':
                new_name = get_name_transformation(name, 'female')
                if new_name != name:
                    instructions.append(f"- {name} → {new_name} (MALE → FEMALE)")
                else:
                    instructions.append(f"- {name} (MALE → FEMALE)")
            elif gender == 'female':
                new_name = get_name_transformation(name, 'male')
                if new_name != name:
                    instructions.append(f"- {name} → {new_name} (FEMALE → MALE)")
                else:
                    instructions.append(f"- {name} (FEMALE → MALE)")
            else:
                instructions.append(f"- {name} (UNKNOWN → specify gender based on context)")
    
    instructions.append("")
    instructions.append("REMEMBER: These are EXPLICIT instructions. Follow them exactly.")
    
    return "\n".join(instructions)