# imports
import random # for the generation of the unique IDs while still keeping them easy to read by humans
import pandas as pd
import spacy
import neuralcoref
import configparser

# read variables from a CONFIG FILE
configfile_name = "../config.ini"
#Read config.ini file
config = configparser.ConfigParser()
config.read(configfile_name)

# FIXED variables
PROTAGONIST_REPLACEMENT_NAME = config.get('prideandprejudice', 'PROTAGONIST_REPLACEMENT_NAME')
OTHER_CHARACTER_SAME_NAME_CHANGE = config.get('prideandprejudice', 'OTHER_CHARACTER_SAME_NAME_CHANGE')
SELECTED_PUCTUATION = ['.', ',', ';', ':', '!', '?']

MALE_PRONOUNS = ["he", 'him', 'his', 'himself']
FEMALE_PRONOUNS = ["she", 'her', 'hers', 'herself']

# we want to avoid regendering all coreferences which are between quotation marks
OPENING_QUOTES = set(['"', '“'])
CLOSING_QUOTES = set(['"', '”'])
inside_dialog = False

# detect the gender
is_female = True

# load needed language resources
nlp = spacy.load('en')
neuralcoref.add_to_pipe(nlp)

# load Spacy's entity ruler which allows for manual annotation of Named Entities
ruler = nlp.create_pipe("entity_ruler")

def find_the_best_replacement_word(word, pos_tag):
    is_female = False

    if word.lower() == 'her':
        is_female = True

    if word.lower() == 'she':
        is_female = True

    # change pronouns from female to male
    if is_female and pos_tag == 'poss':
        return 'his'
    if is_female and pos_tag == 'dobj':
        return 'him'
    if is_female and pos_tag == 'nsubj':
        return 'he'

    # change pronouns from male to female
    if not is_female and pos_tag == 'poss':
        return 'hers'
    if not is_female and pos_tag == 'dobj':
        return 'her'
    if not is_female and pos_tag == 'nsubj':
        return 'she'


# load the Pride & Prejudice data
excerpts = pd.read_excel('../data/Sample_Paragraphs.xlsx', 'Sheet1')
text = excerpts.loc[8].Paragraph
protagonist = excerpts.loc[8].Character
gender = excerpts.loc[8].Gender
if gender.lower() == 'female':
    is_female = True
else:
    is_female = False

gendered_pronouns = None
if is_female:
    gendered_pronouns = FEMALE_PRONOUNS
else:
    gendered_pronouns = MALE_PRONOUNS

# Count how many times the name of the character to be re-genders occurs in the texts
### we do not split the character name of Mrs. Bennet

### see if spacy removes words which are not named entities, such as `Mrs.` and `the`
print('--------')
doc = nlp(protagonist)
found_entities = doc.ents != ()
if not found_entities: # when no NEs have been found - explicitly label the protagonist's name as a NE
    ruler.add_patterns([{"label": "PERSON", "pattern": protagonist}])
    nlp.add_pipe(ruler)

# a. split the excerpt into paragraphs when the char sequence \n\n is detected
paragraphs = text.split('\n\n')
print('There are', len(paragraphs), 'paragraphs detected.')
print("-------")

# assign unique ids for the pronouns of the correferences in the protagonist's cluster
unique_id = random.randint(1000, 9999) # select at random a 4-digit number

# b. find the references to the protagonist in each paragraph
para_count = 1
for paragraph in paragraphs:

    # count how many times we expect the protagonist's name to occur in the current paragraph
    name_count = paragraph.count(protagonist)

    if PROTAGONIST_REPLACEMENT_NAME in paragraph:
        # change the other character's name to something different
        paragraph = paragraph.replace(PROTAGONIST_REPLACEMENT_NAME, OTHER_CHARACTER_SAME_NAME_CHANGE)

    doc = nlp(paragraph)
    has_found_corefs = doc._.has_coref

    if has_found_corefs and name_count < 1: # ERROR HANDLING
        print('\nCAUTION: we have found co-references to the name of the main protagonist is this paragraph, where there should be any....')
        regendered_paragraph = paragraph
    else:
        coref_clusters = doc._.coref_clusters

        # iterate over the co-reference CLUSTERS found and SELECT ONLY the one with the name of the protagonist
        protagonist_cluster = []

        for i in range(len(doc._.coref_clusters)):
            current_cluster = coref_clusters[i]
            cluster_text = coref_clusters[i].main.text
            if cluster_text == protagonist:
                protagonist_cluster = current_cluster
        print("-------")

        # overwrite the co-reference cluster with only the one of the protagonist
        doc._.coref_clusters = protagonist_cluster

        reference_dict = {}

        correct_protagonist_cluster = []
        for i in range(len(doc._.coref_clusters)):
            current_coreference = doc._.coref_clusters[i]
            # sometimes we need to exclude some of the pronoun coreferences - when they are not of the same gender as the protagonist
            # we do this by getting all coreferences of length 1 (e.g. one-word ones) which are pronouns and comparing their gender to the gender of the protagonist
            if len(current_coreference) == 1 and current_coreference[0].tag_.startswith('PRP'):
                # check the gender
                if current_coreference[0].text.lower() in gendered_pronouns:
                    start_span_index = current_coreference.start
                    end_span_index = current_coreference.end
                    reference_dict[start_span_index] = end_span_index

                    correct_protagonist_cluster.append(current_coreference[0].text)
            else:
                start_span_index = current_coreference.start
                end_span_index = current_coreference.end
                reference_dict[start_span_index] = end_span_index

                correct_protagonist_cluster.append(current_coreference)

        # print('CORRECTED PROTAGONIST CLUSTER:', correct_protagonist_cluster)

        regendered_paragraph = ''

        # iterate over all spacy spans in the paragraph AND REPLACE THE COREFERENCES
        i = 0
        while i < len(doc):
            word = doc[i].text
            pos_tag =  doc[i].dep_

            if word in OPENING_QUOTES:
                inside_dialog = True


            if (i not in reference_dict) and (word in CLOSING_QUOTES and inside_dialog):
                regendered_paragraph += word
                # if the word is one of those punctuations, remove the white space before it (e.g. the last character)
                if word in SELECTED_PUCTUATION:
                    regendered_paragraph = regendered_paragraph[:-2]
                    regendered_paragraph += word
                regendered_paragraph += " "

            if i in reference_dict and not inside_dialog:
                word = doc[i:reference_dict[i]].text
                replacement = find_the_best_replacement_word(word, pos_tag)
                if replacement != None: # error handling
                    replacement += ", ID " + str(unique_id) + "," # printing the unique ID of the coreference for clarity
                if word == protagonist:
                    # print('YESSSS, we are replacing the actual name of the protagonist')
                    replacement = PROTAGONIST_REPLACEMENT_NAME
                # print('replacement', replacement, pos_tag, doc[i].pos_, doc[i].tag_, doc[i].shape_)
                # print(replacement, "|", doc[i:reference_dict[i]].text)
                regendered_paragraph += replacement
                regendered_paragraph += " "
                i = reference_dict[i] - 1

            if word in CLOSING_QUOTES and inside_dialog:
                inside_dialog = False
            i += 1

    print(regendered_paragraph)
    print('--------------------------------------------------------, Next paragraph...')

    para_count += 1


