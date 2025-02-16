from book_analyzer import BookAnalyzer
from main import BookAnalysisConfig
from character_analysis import save_character_analysis
import re
from typing import Optional
import json
import subprocess

class Mention:
    def __init__(self, mention_type, context, text, confidence):
        self.mention_type = mention_type
        self.context = context
        self.text = text
        self.confidence = confidence

class Character:
    def __init__(self, name, role, gender, mentions, name_variants):
        self.name = name
        self.role = role
        self.gender = gender
        self.mentions = mentions
        self.name_variants = name_variants

def extract_first_chapters(text: str, num_chapters: int = 3) -> str:
    """Extract first N chapters for quick testing."""
    # Find all chapter markers
    chapter_pattern = r'(?i)^(?:chapter|volume)\s+([IVXLCDM]+|\d+)'
    matches = list(re.finditer(chapter_pattern, text, re.MULTILINE))
    
    if len(matches) < num_chapters + 1:  # +1 for next chapter boundary
        return text
        
    # Get text from start to beginning of chapter after our target
    end_pos = matches[num_chapters].start()
    return text[:end_pos].strip()

def get_clean_mention_context(mention, max_length=100):
    """Get clean, meaningful context for a mention."""
    context = mention.context.strip()
    
    # Skip if context is too short or contains metadata
    if len(context) < 10 or any(x in context.lower() for x in 
        ['copyright', 'project gutenberg', 'illustration', 'chapter']):
        return None
    
    # Clean up the context
    # Remove line numbers and other noise
    context = re.sub(r'\d+\s*$', '', context)
    context = re.sub(r'^\s*\d+\s*', '', context)
    context = re.sub(r'[\r\n]+', ' ', context)
    context = re.sub(r'\s+', ' ', context)
    
    # Find the mention text in the context
    mention_start = context.find(mention.text)
    if mention_start == -1:  # Should never happen
        return None
    
    # Look for sentence boundaries
    sentence_start = mention_start
    while sentence_start > 0 and not context[sentence_start-1] in {'.', '!', '?', '\n'}:
        sentence_start -= 1
        if mention_start - sentence_start > max_length:
            break
    
    sentence_end = mention_start + len(mention.text)
    while sentence_end < len(context) and not context[sentence_end] in {'.', '!', '?', '\n'}:
        sentence_end += 1
        if sentence_end - mention_start > max_length:
            break
    
    # Extract the sentence
    context = context[sentence_start:sentence_end].strip()
    
    # Ensure we don't cut off in the middle of a word
    if len(context) > max_length:
        # Try to break at punctuation
        for punct in ['. ', '! ', '? ', ', ', '; ']:
            break_point = context.rfind(punct, 0, max_length)
            if break_point != -1:
                return context[:break_point+1] + '...'
        
        # Fall back to word boundary
        break_point = context.rfind(' ', 0, max_length)
        if break_point != -1:
            return context[:break_point] + '...'
    
    return context

def get_first_meaningful_mention(char: Character) -> Optional[Mention]:
    """Get the first meaningful mention, prioritizing high-confidence name mentions."""
    # First try to find a high-confidence name mention
    for mention in char.mentions:
        if mention.mention_type == 'name' and mention.confidence > 0.8:
            context = mention.context.strip()
            # Skip if context is too short or contains metadata
            if len(context) > 10 and not any(x in context.lower() for x in 
                ['copyright', 'project gutenberg', 'illustration', 'chapter']):
                return mention
    
    # Fall back to any mention with good confidence
    for mention in char.mentions:
        if mention.confidence > 0.8:
            context = mention.context.strip()
            if len(context) > 10 and not any(x in context.lower() for x in 
                ['copyright', 'project gutenberg', 'illustration', 'chapter']):
                return mention
    
    return None

def get_test_text():
    """Get test text - using just Chapter 1 for faster iteration."""
    text = """Chapter I.

It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.

However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful property of some one or other of their daughters.

"My dear Mr. Bennet," said his lady to him one day, "have you heard that Netherfield Park is let at last?"

Mr. Bennet replied that he had not.

"But it is," returned she; "for Mrs. Long has just been here, and she told me all about it."

Mr. Bennet made no answer.

"Do you not want to know who has taken it?" cried his wife impatiently.

"_You_ want to tell me, and I have no objection to hearing it."

This was invitation enough.

"Why, my dear, you must know, Mrs. Long says that Netherfield is taken by a young man of large fortune from the north of England; that he came down on Monday in a chaise and four to see the place, and was so much delighted with it, that he agreed with Mr. Morris immediately; that he is to take possession before Michaelmas, and some of his servants are to be in the house by the end of next week."

"What is his name?"

"Bingley."

"Is he married or single?"

"Oh! Single, my dear, to be sure! A single man of large fortune; four or five thousand a year. What a fine thing for our girls!"

"How so? How can it affect them?"

"My dear Mr. Bennet," replied his wife, "how can you be so tiresome! You must know that I am thinking of his marrying one of them."

"Is that his design in settling here?"

"Design! Nonsense, how can you talk so! But it is very likely that he _may_ fall in love with one of them, and therefore you must visit him as soon as he comes."

"I see no occasion for that. You and the girls may go, or you may send them by themselves, which perhaps will be still better, for as you are as handsome as any of them, Mr. Bingley may like you the best of the party."

"My dear, you flatter me. I certainly _have_ had my share of beauty, but I do not pretend to be anything extraordinary now. When a woman has five grown-up daughters, she ought to give over thinking of her own beauty."

"In such cases, a woman has not often much beauty to think of."

"But, my dear, you must indeed go and see Mr. Bingley when he comes into the neighbourhood."

"It is more than I engage for, I assure you."

"But consider your daughters. Only think what an establishment it would be for one of them. Sir William and Lady Lucas are determined to go, merely on that account, for in general, you know, they visit no newcomers. Indeed you must go, for it will be impossible for _us_ to visit him if you do not."

"You are over-scrupulous, surely. I dare say Mr. Bingley will be very glad to see you; and I will send a few lines by you to assure him of my hearty consent to his marrying whichever he chooses of the girls; though I must throw in a good word for my little Lizzy."

"I desire you will do no such thing. Lizzy is not a bit better than the others; and I am sure she is not half so handsome as Jane, nor half so good-humoured as Lydia. But you are always giving _her_ the preference."

"They have none of them much to recommend them," replied he; "they are all silly and ignorant like other girls; but Lizzy has something more of quickness than her sisters."

"Mr. Bennet, how _can_ you abuse your own children in such a way? You take delight in vexing me. You have no compassion for my poor nerves."

"You mistake me, my dear. I have a high respect for your nerves. They are my old friends. I have heard you mention them with consideration these last twenty years at least."

"Ah, you do not know what I suffer."

"But I hope you will get over it, and live to see many young men of four thousand a year come into the neighbourhood."

"It will be no use to us, if twenty such should come, since you will not visit them."

"Depend upon it, my dear, that when there are twenty, I will visit them all."

Mr. Bennet was so odd a mixture of quick parts, sarcastic humour, reserve, and caprice, that the experience of three-and-twenty years had been insufficient to make his wife understand his character. _Her_ mind was less difficult to develop. She was a woman of mean understanding, little information, and uncertain temper. When she was discontented, she fancied herself nervous. The business of her life was to get her daughters married; its solace was visiting and news."""
    return text

def test_analyzer(quick_test: bool = True):
    """Test the book analyzer with option for quick testing."""
    if quick_test:
        text = get_test_text()
    else:
        with open('pride_and_prejudice_full.txt', 'r') as f:
            text = f.read()
    
    print("Testing with Chapter 1 only..." if quick_test else "Testing with full book...")
    print(f"Test text length: {len(text)} chars\n")
    
    config = BookAnalysisConfig()
    analyzer = BookAnalyzer(config)
    
    print("Finding chapters...")
    chapters = analyzer._find_chapters(text)
    print(f"\nChapters found: {len(chapters)}")
    print("\nFirst 5 chapters:")
    for ch in chapters[:5]:
        print(f"Chapter {ch.number}{': ' + ch.title if ch.title else ''}")
        print(f"Position: {ch.start_pos}-{ch.end_pos}")
        print(f"Confidence: {ch.confidence}")
        print(f"Preview: {text[ch.start_pos:ch.start_pos+50]}...")
        print()
    
    print("\nAnalyzing characters...")
    characters = analyzer.analyze_characters(text)
    
    # Save results
    output_file = "quick_test_characters.json" if quick_test else "pride_and_prejudice_characters.json"
    save_character_analysis(characters, output_file)
    
    # Count mentions by type and confidence
    name_mentions = sum(len([m for m in char.mentions if m.mention_type == 'name']) 
                       for char in characters.values())
    high_conf_pronouns = sum(len([m for m in char.mentions 
                                 if m.mention_type in ['pronoun', 'possessive'] 
                                 and m.confidence > 0.8]) 
                            for char in characters.values())
    low_conf_pronouns = sum(len([m for m in char.mentions 
                                if m.mention_type in ['pronoun', 'possessive'] 
                                and m.confidence <= 0.8]) 
                           for char in characters.values())
    
    print(f"\nTotal mentions: {name_mentions + high_conf_pronouns + low_conf_pronouns}")
    print(f"Name mentions: {name_mentions}")
    print(f"High confidence pronouns: {high_conf_pronouns}")
    print(f"Low confidence pronouns: {low_conf_pronouns}")
    
    # Print summary of main characters (top 5 by name mentions)
    print("\nTop 5 characters by mentions:")
    sorted_chars = sorted(characters.values(), 
                        key=lambda x: len([m for m in x.mentions if m.mention_type == 'name']), 
                        reverse=True)
    for char in sorted_chars[:5]:
        name_count = len([m for m in char.mentions if m.mention_type == 'name'])
        high_conf_count = len([m for m in char.mentions 
                             if m.mention_type in ['pronoun', 'possessive'] 
                             and m.confidence > 0.8])
        low_conf_count = len([m for m in char.mentions 
                            if m.mention_type in ['pronoun', 'possessive'] 
                            and m.confidence <= 0.8])
        
        print(f"\n{char.name}:")
        print(f"  Role: {char.role}")
        print(f"  Gender: {char.gender}")
        print(f"  Mentions: {name_count + high_conf_count + low_conf_count}")
        print(f"    Names: {name_count}")
        print(f"    High confidence pronouns: {high_conf_count}")
        print(f"    Low confidence pronouns: {low_conf_count}")
        print(f"  Variants: {', '.join(char.name_variants)}")
        
        # Get first meaningful mention
        first_mention = get_first_meaningful_mention(char)
        if first_mention:
            context = get_clean_mention_context(first_mention)
            if context:
                print(f"  First mention: {context} (confidence: {first_mention.confidence:.2f})")

    # Save results as JSON
    output = {}
    for char in characters.values():
        output[char.name] = {
            'name': char.name,
            'gender': char.gender,
            'role': char.role,
            'mentions': [{
                'type': m.mention_type,
                'text': m.text,
                'start': m.start,
                'end': m.end,
                'confidence': m.confidence
            } for m in char.mentions]
        }
    
    with open('test_output.json', 'w') as f:
        json.dump(output, f, indent=2)
        
    # Run accuracy test
    print("\nRunning accuracy test...")
    subprocess.run(['python3', 'test_accuracy.py'])

if __name__ == '__main__':
    test_analyzer(quick_test=True)  # Set to False for full book test
