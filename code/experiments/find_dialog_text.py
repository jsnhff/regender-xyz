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

# Count how many times the name of the character to be re-genders occurs in the texts

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

    dialog_dict = {}
    i = 0
    has_started_recording = False
    opening_index = None
    closing_index = None
    while i < len(doc):
        word = doc[i].text

        # check if we are not starting a quotation
        if word in OPENING_QUOTES:
            has_started_recording = True
            opening_index = i
            old_i = i

        # check if we are not finishing a quotation
        if word in CLOSING_QUOTES and has_started_recording:
            closing_index = i
            dialog_dict[opening_index] = (opening_index, closing_index)

        i += 1

    # remove all quotes
    quoteless_paragraph = ''
    i = 0
    while i < len(doc):
        word = doc[i].text
        if i not in dialog_dict:
            quoteless_paragraph += word
            quoteless_paragraph += ' '
            i += 1
        else:
            quoteless_paragraph += '-'
            quoteless_paragraph += ' '
            i += dialog_dict[i][1] + 1

    print(quoteless_paragraph)


