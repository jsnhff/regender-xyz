# imports
import random # for the generation of the unique IDs while still keeping them easy to read by humans
import pandas as pd
import spacy
import neuralcoref

# FIXED variables
SELECTED_PUCTUATION = ['.', ',', ';', ':', '!', '?']
REPLACEMENT_START = '>>>'
REPLACEMENT_END = '<<<'

# detect the gender
is_female = True

# load needed language resources
nlp = spacy.load('en')
neuralcoref.add_to_pipe(nlp)

# load Spacy's entity ruler which allows for manual annotation of Named Entities
ruler = nlp.create_pipe("entity_ruler")


# load the Sound and Fury data
excerpts = pd.read_excel('../data/Sample_Paragraphs.xlsx', 'Sheet1')
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

    # count how many times we expect the protagonist's name to occur in the current paragraph (IF WE HAVE THE PROTAGONIST'S NAME)
    name_count = paragraph.count(protagonist)

    doc = nlp(paragraph)
    has_found_corefs = doc._.has_coref

    coref_clusters = doc._.coref_clusters

    protagonist_cluster = None
    for cluster in coref_clusters:
        if cluster.main.text == 'Sarah':
            protagonist_cluster = cluster

    # overwrite the co-reference cluster with only the one of the protagonist
    doc._.coref_clusters = protagonist_cluster

    # Now let's see what would get replaced
    reference_dict = {}
    correct_protagonist_cluster = []

    for i in range(len(doc._.coref_clusters)):
        current_coreference = doc._.coref_clusters[i]

        start_span_index = current_coreference.start
        end_span_index = current_coreference.end
        reference_dict[start_span_index] = end_span_index


    regendered_paragraph = ''
    i = 0
    while i < len(doc):
        word = doc[i].text
        pos_tag =  doc[i].dep_
        if i not in reference_dict:
            regendered_paragraph += word
            regendered_paragraph += ' '
        else:
            regendered_paragraph += REPLACEMENT_START
            regendered_paragraph += word
            regendered_paragraph += REPLACEMENT_END
            regendered_paragraph += ' '
        i += 1

    print(regendered_paragraph)
