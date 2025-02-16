"""Tests for character detection accuracy."""

CHAPTER_1_3_CHARACTERS = {
    "Mr. Bennet": {
        "role": "father of five daughters",
        "gender": "male",
        "variants": ["Mr. Bennet", "Mr Bennet"],
        "pronouns": ["he", "him", "his"],
        "first_mention": "Mr. Bennet was so odd a mixture of quick parts",
    },
    "Mrs. Bennet": {
        "role": "mother obsessed with marrying off her daughters",
        "gender": "female",
        "variants": ["Mrs. Bennet", "Mrs Bennet"],
        "pronouns": ["she", "her", "hers"],
        "first_mention": "Mrs. Bennet was a woman of mean understanding",
    },
    "Mr. Bingley": {
        "role": "wealthy young gentleman",
        "gender": "male",
        "variants": ["Mr. Bingley", "Mr Bingley", "Bingley", "Charles Bingley"],
        "pronouns": ["he", "him", "his"],
        "first_mention": "a single man of large fortune",
    },
    "Jane Bennet": {
        "role": "eldest Bennet daughter",
        "gender": "female",
        "variants": ["Jane", "Miss Bennet", "Miss Jane Bennet"],
        "pronouns": ["she", "her", "hers"],
        "first_mention": "Jane was admired",
    },
    "Elizabeth Bennet": {
        "role": "second eldest Bennet daughter",
        "gender": "female",
        "variants": ["Elizabeth", "Lizzy", "Miss Elizabeth"],
        "pronouns": ["she", "her", "hers"],
        "first_mention": "Elizabeth was obliged to go to Netherfield",
    },
    "Lady Catherine": {
        "role": "wealthy noblewoman",
        "gender": "female",
        "variants": ["Lady Catherine", "Lady Catherine de Bourgh"],
        "pronouns": ["she", "her", "hers"],
        "first_mention": "Lady Catherine was reckoned proud",
    }
}

def test_character_detection():
    """Test that we can detect all major characters in first 3 chapters."""
    from character_analysis import find_characters
    
    # Load test text
    with open("test_data/pride_ch1_3.txt") as f:
        text = f.read()
    
    # Find characters
    characters = find_characters(text)
    
    # Check that we found all expected characters
    for name, details in CHAPTER_1_3_CHARACTERS.items():
        assert name in characters, f"Missing character: {name}"
        char = characters[name]
        
        # Check basic properties
        assert char.role == details["role"], f"Wrong role for {name}"
        assert char.gender == details["gender"], f"Wrong gender for {name}"
        
        # Check name variants
        for variant in details["variants"]:
            assert variant in char.name_variants, f"Missing variant {variant} for {name}"
            
        # Check pronouns
        mentions = [m.text.lower() for m in char.mentions]
        for pronoun in details["pronouns"]:
            assert any(pronoun == m for m in mentions), f"Missing pronoun {pronoun} for {name}"
            
        # Check first mention
        first = next((m for m in char.mentions if m.mention_type == "name"), None)
        assert first, f"No first mention found for {name}"
        assert details["first_mention"] in first.context, f"Wrong first mention for {name}"
