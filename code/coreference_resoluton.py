# imports
import random # for the generation of the unique IDs while still keeping them easy to read by humans
import configparser # to read the variable values from the config file

from aux.nlp_helper import find_the_best_replacement_word, add_protagonist_as_a_named_entity, find_protagonist_coreference_cluster, find_all_protagonist_coreferences, regender_paragraph # load auxiliary functions to help regendering words
from aux.load import load_spacy_neuralcoref, load_exceprt_data # load auxiliary functions to load NLP libraries & data

# read variables from a CONFIG FILE
configfile_name = "../config.ini"
config = configparser.ConfigParser()
config.read(configfile_name)

# we want to avoid regendering all coreferences which are between quotation marks
OPENING_QUOTES = config.get('quotes', 'OPENING').split('|||')
CLOSING_QUOTES = config.get('quotes', 'CLOSING').split('|||')
inside_dialog = False

# detect the gender
is_female = True

# load needed language resources
nlp, ruler = load_spacy_neuralcoref()

# load the Pride & Prejudice data - give the argument 8
# load the The Sound anf Fury data - give the argument 1
text, text_title, protagonist, gender, is_female, gendered_pronouns = load_exceprt_data(1)
text_title = text_title.replace(' ', '').lower() # using this variable to read from the config.ini file

# FIXED variables
PROTAGONIST_REPLACEMENT_NAME = config.get(text_title, 'PROTAGONIST_REPLACEMENT_NAME')
OTHER_CHARACTER_SAME_NAME_CHANGE = config.get(text_title, 'OTHER_CHARACTER_SAME_NAME_CHANGE')
# END of reading FIXED variables

#####################
#### START LOGIC ####
#####################

# in case spacy does not regognize the protanogist's name we have as a Named Entity, add t manually
print('--------')
ruler = add_protagonist_as_a_named_entity(nlp, protagonist, ruler)
nlp.add_pipe(ruler)

# a. split the excerpt into paragraphs when the char sequence \n\n is detected
paragraphs = text.split('\n\n')
print('There are', len(paragraphs), 'paragraphs detected.')
print("-------")

# assign unique ids for the pronouns of the coreferences in the protagonist's cluster
unique_id = random.randint(1000, 9999) # select at random a 4-digit number

# b. find the references to the protagonist in each paragraph
para_count = 1

for paragraph in paragraphs:

    # count how many times we expect the protagonist's name to occur in the current paragraph
    name_count = paragraph.count(protagonist)

    if PROTAGONIST_REPLACEMENT_NAME in paragraph:
        # change the other character's name to something different
        paragraph = paragraph.replace(PROTAGONIST_REPLACEMENT_NAME, OTHER_CHARACTER_SAME_NAME_CHANGE)

    # find all coreferences of the protanogist in this paragraphs
    doc = nlp(paragraph)
    has_found_corefs = doc._.has_coref

    if has_found_corefs and name_count < 1: # ERROR HANDLING
        print('\nCAUTION: we have found co-references to the name of the main protagonist is this paragraph, where there should be any....')
        regendered_paragraph = paragraph
    else:
        # iterate over the co-reference CLUSTERS found and SELECT ONLY the one with the name of the protagonist
        doc = find_protagonist_coreference_cluster(doc, protagonist)

        # clean the protagonist's coreference cluster -> e.g when the protagonist is a woman but we have coreferences such as 'he' and 'him'
        reference_dict = find_all_protagonist_coreferences(doc, gendered_pronouns)
        # regender paragraph
        regendered_paragraph = regender_paragraph(text_title, doc, protagonist, unique_id, reference_dict)

    print(regendered_paragraph)
    print('--------------------------------------------------------, Next paragraph...')

    para_count += 1

#####################
##### END LOGIC #####
#####################
