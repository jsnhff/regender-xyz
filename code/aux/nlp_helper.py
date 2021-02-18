import configparser # to read the variable values from the config file
import neuralcoref
import subprocess, os, random

# get the GIT root folder, e.g. the root folder of the project
root_dir = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True).stdout.decode('utf-8').rstrip()

# read variables from a CONFIG FILE
configfile_name = root_dir + os.sep + "config.ini"
config = configparser.ConfigParser()
config.read(configfile_name)

# reading FIXED variables
DELIMITER = config.get('delimiter', 'IN_CONFIG')
SELECTED_PUNCTUATION = config.get('misc', 'PUNCTUATION').split(DELIMITER)
OPENING_QUOTES = config.get('quotes', 'OPENING').split(DELIMITER)
CLOSING_QUOTES = config.get('quotes', 'CLOSING').split(DELIMITER)
# END of reading FIXED variables

# finds the best replacement for pronouns when regendering
# TODO: the cases of herself/himself are not handled here yet
def find_the_best_replacement_word(word, dep_tag, is_female):

    # change pronouns from female to male
    # find all English dependency pos tag reference here -> https://spacy.io/api/annotation#pos-tagging
    if is_female and dep_tag == 'poss': # DEP tag = possession modifier
        word = change_word(word, 'her', 'his')
        return word
    if is_female and dep_tag == 'dobj': # DEP tag = direct object
        word = change_word(word, 'her', 'him')
        return word
    if is_female and dep_tag == 'nsubj': # DEP tag = nominal subject
        word = change_word(word, 'she', 'he')
        return word
    if is_female and dep_tag == 'pobj': # DEP tag = object of preposition
        word = change_word(word, 'her', 'his')
        return word
    if is_female and dep_tag == 'attr': # DEP tag = object of preposition
        word = change_word(word, 'hers', 'his')
        return word

    # change pronouns from male to female
    if not is_female and dep_tag == 'poss': # DEP tag = possession modifier
        word = change_word(word, 'his', 'her')
        return word
    if not is_female and dep_tag == 'dobj': # DEP tag = direct object
        word = change_word(word, 'him', 'her')
        return word
    if not is_female and dep_tag == 'nsubj': # DEP tag = nominal subject
        word = change_word(word, 'he', 'she')
        return word
    if not is_female and dep_tag == 'pobj': # DEP tag = object of preposition
        word = change_word(word, 'him', 'her')
        return word
    if not is_female and dep_tag == 'attr': # DEP tag = object of preposition
        word = change_word(word, 'his', 'hers')
        return word

def change_word(original_word, string_to_replace, replacement_word):
    starts_with_capital_letter = original_word[0].isupper()
    original_word = original_word.lower()
    original_word = original_word.replace(string_to_replace, replacement_word)

    if starts_with_capital_letter:
        original_word = original_word[0].upper() + original_word[1:]

    return original_word

def add_character_as_a_named_entity(nlp, protagonist, ruler):
    doc = nlp(protagonist)
    found_entities = doc.ents != ()
    if not found_entities:  # when no NEs have been found - explicitly label the protagonist's name as a NE
        ruler.add_patterns([{"label": "PERSON", "pattern": protagonist}])
    return ruler

# iterate over the co-reference CLUSTERS found and SELECT ONLY the one with the name of the protagonist
def find_protagonist_coreference_cluster(nlp, doc, paragraph, protagonist, additional_character):
    protagonist_name = protagonist.get_name()
    is_female = protagonist.get_is_female()
    gendered_pronouns = protagonist.get_gendered_pronouns()

    protagonist_cluster = select_protagonist_cluster(doc, protagonist_name)

    # because of Beloved
    # what happens when there is no cluster which is headed by the protagonist's name
    if protagonist_cluster == None:

        # add conversion dictionary to neuralcoref TO ADD RARE WORDS
        nlp.remove_pipe("neuralcoref")
        conv_dict = {}
        conv_dict = add_convertion_dictionary_entry(conv_dict, protagonist_name, is_female, 'protagonist')
        if additional_character != None:
            # N.B. adding rare words ONLY WORKS FOR SINGLE WORDS - Phyllis, and not group words, e.g. Aunt Phyllis.
            # N.B. keep a look at the documentation for any changes -> https://github.com/huggingface/neuralcoref
            conv_dict = add_convertion_dictionary_entry(conv_dict, additional_character, is_female, 'character')
        neuralcoref.add_to_pipe(nlp, conv_dict=conv_dict)
        doc = nlp(paragraph)

        protagonist_cluster = select_protagonist_cluster(doc, protagonist_name)


        # enrich the coreferences of freshly added rare word cluster -> protagonist_cluster.mentions
        for i in range(len(doc._.coref_clusters)):
            current_cluster_mentions = doc._.coref_clusters[i].mentions
            cluster_text = doc._.coref_clusters[i].main.text
            if any(map(cluster_text.__contains__, gendered_pronouns)):
                protagonist_cluster.mentions = protagonist_cluster.mentions + current_cluster_mentions

    # overwrite the co-reference cluster with only the one of the protagonist
    doc._.coref_clusters = protagonist_cluster

    return doc

def select_protagonist_cluster(doc, protagonist_name):
    protagonist_cluster = None
    for i in range(len(doc._.coref_clusters)):
        current_cluster = doc._.coref_clusters[i]
        cluster_text = doc._.coref_clusters[i].main.text
        cluster_text = doc._.coref_clusters[i].main.text
        if cluster_text == protagonist_name:
            protagonist_cluster = current_cluster

    return protagonist_cluster

def add_convertion_dictionary_entry(conv_dict, protagonist, is_female, role):
    if is_female:
        conv_dict[protagonist] = ['woman', 'girl', role]
    else:
        conv_dict[protagonist] = ['man', 'boy', role]
    return conv_dict

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

def regender_outside_quotes(book_title, word, dep_tag, protagonist, doc, i, reference_dict, regendered_paragraph):
    protagonist_name = protagonist.get_name()
    is_female = protagonist.get_is_female()

    if (i not in reference_dict):
        regendered_paragraph += word
        # if the word is one of those punctuations, remove the white space before it (e.g. the last character)
        if word in SELECTED_PUNCTUATION:
            regendered_paragraph = regendered_paragraph[:-2]
            regendered_paragraph += word
        regendered_paragraph += " "

    if i in reference_dict:
        word = doc[i:reference_dict[i]].text
        replacement = find_the_best_replacement_word(word, dep_tag, is_female)

        if replacement != None:  # error handling
            replacement += ", ID " + str(random.randint(1000, 9999)) + ","  # printing the unique ID of the coreference for clarity
        if word == protagonist_name:
            # print('YESSSS, we are replacing the actual name of the protagonist')
            PROTAGONIST_REPLACEMENT_NAME = config.get(book_title, 'PROTAGONIST_REPLACEMENT_NAME')
            replacement = PROTAGONIST_REPLACEMENT_NAME

        regendered_paragraph += replacement
        regendered_paragraph += " "
        i = reference_dict[i] - 1

    return i, regendered_paragraph

def regender_paragraph(book_title, doc, protagonist, is_female, reference_dict):

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
        dep_tag = doc[i].dep_ # we use the Syntactic dependency relation instead of the POS
        # here we mostly handle avoid manipulating text between quotation marks
        if inside_dialog:
            has_read_some_dialog = True
            regendered_paragraph += word
            regendered_paragraph += ' '
        else:
            # HERE IS WHERE THE REGENDERING MAGIC HAPPENS
            i, regendered_paragraph = regender_outside_quotes(book_title, word, dep_tag, protagonist, doc, i, reference_dict, regendered_paragraph)
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


def find_word_indices_in_paragraph(entities, is_proper_names):
    words = []
    indices = []
    for entity in entities:
        entity = entity[-1]
        if is_proper_names:
            if entity.pos_ == 'PROPN': # PROPN == proper name
                words.append(entity.text)
                indices.append(entity.i)
        else:
            words.append(entity.text)
            indices.append(entity.i)
    return words, indices