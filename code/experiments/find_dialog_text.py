# imports
import random # for the generation of the unique IDs while still keeping them easy to read by humans
import pandas as pd
import spacy
import neuralcoref

# FIXED variables
SELECTED_PUCTUATION = ['.', ',', ';', ':', '!', '?']
REPLACEMENT_START = '>>>'
REPLACEMENT_END = '<<<'

OPENING_QUOTES = set(['"', '“'])
CLOSING_QUOTES = set(['"', '”'])
inside_dialog = False
has_read_some_dialog = False
just_closed_dialog = False

# detect the gender
is_female = True

# load needed language resources
nlp = spacy.load('en')
neuralcoref.add_to_pipe(nlp)

# load Spacy's entity ruler which allows for manual annotation of Named Entities
ruler = nlp.create_pipe("entity_ruler")


# load the Sound and Fury data
excerpts = pd.read_excel('../../data/Sample_Paragraphs.xlsx', 'Sheet1')
text = excerpts.loc[1].Paragraph
protagonist = excerpts.loc[1].Character
gender = excerpts.loc[1].Gender
if gender.lower() == 'female':
    is_female = True
else:
    is_female = False

# FORCE change all quotes to simple quotes
text = text.replace('“', '"')
text = text.replace('”', '"')
# END FORCE change all quotes to simple quotes


## see if spacy removes words which are not named entities, such as `Mrs.` and `the`
print('--------')
doc = nlp(protagonist)
found_entities = doc.ents != ()
if not found_entities: # when no NEs have been found - explicitly label the protagonist's name as a NE
    ruler.add_patterns([{"label": "PERSON", "pattern": protagonist}])
    nlp.add_pipe(ruler)

# a. split the excerpt into paragraphs when the char sequence \n\n is detected
paragraphs = text.split('\n\n')
print('There are', len(paragraphs), 'paragraph(s) detected.')
print("-------")

# assign unique ids for the pronouns of the correferences in the protagonist's cluster
unique_id = random.randint(1000, 9999) # select at random a 4-digit number

# b. find the references to the protagonist in each paragraph
para_count = 1

print(text)
print('----------------------')
print('----------------------')

for paragraph in paragraphs:

    doc = nlp(paragraph)

    i = 0

    quoteless_paragraph = ''

    while i < len(doc):
        word = doc[i].text

        if inside_dialog:
            has_read_some_dialog = True
            quoteless_paragraph += 'YYY'
            quoteless_paragraph += ' '
        else:
            quoteless_paragraph += word
            quoteless_paragraph += ' '

        # check if we are not finishing a quotation
        if word in CLOSING_QUOTES and inside_dialog and has_read_some_dialog:
            inside_dialog = False
            has_read_some_dialog = False
            just_closed_dialog = True
            quoteless_paragraph += word
            quoteless_paragraph += ' '

        # check if we are not starting a quotation
        if word in OPENING_QUOTES and not just_closed_dialog:
            inside_dialog = True
            just_closed_dialog = False

        just_closed_dialog = False

        i += 1

    print(quoteless_paragraph)


