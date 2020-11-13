# imports
import pandas as pd
import spacy
import neuralcoref

# FIXED variables
PROTAGONIST_REPLACEMENT_NAME = 'REPLACEMENT_NAME'

MALE_PRONOUNS = ["he", 'him', 'his', 'himself']
FEMALE_PRONOUNS = ["she", 'her', 'hers', 'herself']

# detect the gender
is_female = True

# load needed language resources
nlp = spacy.load('en')
neuralcoref.add_to_pipe(nlp)

# load Spacy's entity ruler which allows for manual annotation of Named Entities
ruler = nlp.create_pipe("entity_ruler")

def find_the_best_word(word, pos_tag):
    is_female = False

    if word.lower() == 'her':
        is_female = True

    if word.lower() == 'she':
        is_female = True

    if is_female and pos_tag == 'poss':
        return 'HIS'
    if is_female and pos_tag == 'dobj':
        return 'HIM'
    if is_female and pos_tag == 'nsubj':
        return 'HE'


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

# b. find the references to the protagonist in each paragraph
para_count = 1
for paragraph in paragraphs:
    # paragraph = 'Not all that Mrs. Bennet, however, with the assistance of her five daughters, could ask on the subject, was sufficient to draw from her husband any satisfactory description of Mr. Bingley. He disliked her.'
    print(paragraph)
    # count how many times we expect the protagonist's name to occur in the current paragraph
    name_count = paragraph.count(protagonist)

    doc = nlp(paragraph)
    has_found_corefs = doc._.has_coref
    # ERROR HANDLING
    if has_found_corefs and name_count < 1:
        print('ERROR: we have found co-references to the name of the main protagonist is this paragraph, where there should be any....')
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

        # clean protagonist cluster -> remove pronouns from a different gender
        # protagonist_cluster = remove_different_gender_pronouns(protagonist_cluster)
        print('PROTAGONIST CLUSTER', protagonist_cluster)

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

                correct_protagonist_cluster.append(current_coreference[0].text)

        print('CORRECTED PROTAGONIST CLUSTER:', correct_protagonist_cluster)
        regendered_paragraph = ''

        # iterate over all spacy spans in the paragraph
        i = 0
        while i < len(doc):
            word = doc[i].text
            pos_tag =  doc[i].dep_
            if i not in reference_dict:
                regendered_paragraph += word
                regendered_paragraph += " "
            else:
                replacement = find_the_best_word(word, pos_tag)
                print('replacement', replacement, pos_tag, doc[i].pos_, doc[i].tag_, doc[i].shape_)
                if doc[i:reference_dict[i]].text == protagonist:
                    print('YESSSS')
                    replacement = PROTAGONIST_REPLACEMENT_NAME
                print(type(replacement), "|", replacement, "|", doc[i:reference_dict[i]].text)
                regendered_paragraph += replacement
                regendered_paragraph += " "
                i = reference_dict[i] - 1
            i += 1

        print(regendered_paragraph)
        print('--------------------------------------------------------, Next paragraph...')

        para_count += 1


