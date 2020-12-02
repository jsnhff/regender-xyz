import configparser # to read the variable values from the config file

# read variables from a CONFIG FILE
configfile_name = "../config.ini"
config = configparser.ConfigParser()
config.read(configfile_name)

# reading FIXED variables
DELIMITER = config.get('delimiter', 'IN_CONFIG')
SELECTED_PUNCTUATION = config.get('misc', 'PUNCTUATION').split(DELIMITER)
OPENING_QUOTES = config.get('quotes', 'OPENING').split(DELIMITER)
CLOSING_QUOTES = config.get('quotes', 'CLOSING').split(DELIMITER)
PROTAGONIST_REPLACEMENT_NAME = config.get('prideandprejudice', 'PROTAGONIST_REPLACEMENT_NAME')
# END of reading FIXED variables

# finds the best replacement for pronouns when regendering
# TODO: the cases of herself/himself are not handled here yet
def find_the_best_replacement_word(word, pos_tag):
    is_female = False

    if word.lower() == 'her':
        is_female = True

    if word.lower() == 'she':
        is_female = True

    # change pronouns from female to male
    # find all English dependency pos tag reference here -> https://spacy.io/api/annotation#pos-tagging
    if is_female and pos_tag == 'poss': # POS tag = possession modifier
        return 'his'
    if is_female and pos_tag == 'dobj': # POS tag = direct object
        return 'him'
    if is_female and pos_tag == 'nsubj': # POS tag = nominal subject
        return 'he'
    if is_female and pos_tag == 'pobj': # POS tag = object of preposition
        return 'him'

    # change pronouns from male to female
    if not is_female and pos_tag == 'poss': # POS tag = possession modifier
        return 'hers'
    if not is_female and pos_tag == 'dobj': # POS tag = direct object
        return 'her'
    if not is_female and pos_tag == 'nsubj': # POS tag = nominal subject
        return 'she'
    if not is_female and pos_tag == 'pobj': # POS tag = object of preposition
        return 'her'

def add_protagonist_as_a_named_entity(nlp, protagonist, ruler):
    doc = nlp(protagonist)
    found_entities = doc.ents != ()
    if not found_entities:  # when no NEs have been found - explicitly label the protagonist's name as a NE
        ruler.add_patterns([{"label": "PERSON", "pattern": protagonist}])
    return ruler

# iterate over the co-reference CLUSTERS found and SELECT ONLY the one with the name of the protagonist
def find_protagonist_coreference_cluster(doc, protagonist):
    coref_clusters = doc._.coref_clusters

    protagonist_cluster = []

    for i in range(len(doc._.coref_clusters)):
        current_cluster = coref_clusters[i]
        cluster_text = coref_clusters[i].main.text
        if cluster_text == protagonist:
            protagonist_cluster = current_cluster

    # overwrite the co-reference cluster with only the one of the protagonist
    doc._.coref_clusters = protagonist_cluster
    return doc

# find all coreferences of the protagonist
# output: returns a dictionary
def find_all_protagonist_coreferences(doc, gendered_pronouns):
    reference_dict = {}

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

        else:
            start_span_index = current_coreference.start
            end_span_index = current_coreference.end
            reference_dict[start_span_index] = end_span_index

    return reference_dict

def regender_outside_quotes(word, pos_tag, unique_id, protagonist, doc, i, reference_dict, regendered_paragraph):
    if (i not in reference_dict):
        regendered_paragraph += word
        # if the word is one of those punctuations, remove the white space before it (e.g. the last character)
        if word in SELECTED_PUNCTUATION:
            regendered_paragraph = regendered_paragraph[:-2]
            regendered_paragraph += word
        regendered_paragraph += " "

    if i in reference_dict:
        word = doc[i:reference_dict[i]].text
        replacement = find_the_best_replacement_word(word, pos_tag)
        if replacement != None:  # error handling
            replacement += ", ID " + str(unique_id) + ","  # printing the unique ID of the coreference for clarity
        if word == protagonist:
            # print('YESSSS, we are replacing the actual name of the protagonist')
            replacement = PROTAGONIST_REPLACEMENT_NAME

        regendered_paragraph += replacement
        regendered_paragraph += " "
        i = reference_dict[i] - 1

    return i, regendered_paragraph

def regender_paragraph(doc, protagonist, unique_id, reference_dict):

    # boolean helper variables
    inside_dialog = False
    has_read_some_dialog = False
    just_closed_dialog = False
    # END of booleans helper variables

    regendered_paragraph = ''

    # iterate over all spacy spans in the paragraph AND REPLACE THE COREFERENCES
    i = 0
    while i < len(doc):
        word = doc[i].text
        pos_tag = doc[i].dep_
        # here we mostly handle avoid manipulating text between quotation marks
        if inside_dialog:
            has_read_some_dialog = True
            regendered_paragraph += word
            regendered_paragraph += ' '
        else:
            # HERE IS WHERE THE REGENDERING MAGIC HAPPENS
            i, regendered_paragraph = regender_outside_quotes(word, pos_tag, unique_id, protagonist, doc, i, reference_dict, regendered_paragraph)
            # END: HERE IS WHERE THE REGENDERING MAGIC HAPPENS

        # check if we are not finishing a quotation
        if word in CLOSING_QUOTES and inside_dialog and has_read_some_dialog:
            inside_dialog = False
            has_read_some_dialog = False
            just_closed_dialog = True
            regendered_paragraph += word
            regendered_paragraph += ' '

        # check if we are not starting a quotation
        if word in OPENING_QUOTES and not just_closed_dialog:
            inside_dialog = True
            just_closed_dialog = False

        just_closed_dialog = False
        # END here we mostly handle avoid manipulating text between quotation marks

        i += 1

    return regendered_paragraph