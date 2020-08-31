# imports
import pandas as pd
import spacy
import neuralcoref

# load needed language resources
nlp = spacy.load('en')
neuralcoref.add_to_pipe(nlp)

# load Spacy's entity ruler which allows for manual annotation of Named Entities
ruler = nlp.create_pipe("entity_ruler")

# load the Pride & Prejudice data
excerpts = pd.read_excel('../data/Sample_Paragraphs.xlsx', 'Sheet1')
text = excerpts.loc[8].Paragraph
protagonist = excerpts.loc[8].Character

# Count how many times the name of the character to be re-genders occurs in the texts
### we do not split the character name of Mrs. Bennet

### see if spacy removes words which are not named entities, such as `Mrs.` and `the`
print('--------')
doc = nlp(protagonist)
found_entities = doc.ents != ()
if not found_entities: # when no NEs have been found - explicitly label the protagonist's name as a NE
    ruler.add_patterns([{"label": "PERSON", "pattern": protagonist}])
    nlp.add_pipe(ruler)

# a. split the excerpt into paragraphs when trhe char sequence \n\n is detected
paragraphs = text.split('\n\n')
print('There are', len(paragraphs), 'paragraphs detected.')

# b. find the references to the protagonist in each paragraph
for paragraph in paragraphs:
    print(paragraph)
    # count how many times we expect the protagonist's name to occur in the current paragraph
    name_count = paragraph.count(protagonist)

    doc = nlp(paragraph)
    has_found_corefs = doc._.has_coref
    # ERROR HANDLING
    if has_found_corefs and name_count < 1:
        print('ERROR: we have found co-references to the name of the main protagonist is this paragraph, where there should be any....')
    else:
        print('/n')
        coref_clusters = doc._.coref_clusters
        print(type(doc._.coref_clusters))
        print('&&&&&&&&&&&&&')
        # TYPE of coref_clusters[0] -> neuralcoref CLUSTER
        # TYPE of coref_clusters[0].main -> spacy SPAN
        # iterate over the coreference CLUSTERS found and DELETE all expect the one with the name of the protagonist
        for i in range(len(doc._.coref_clusters)):
            cluster_text = coref_clusters[i].main.text
            print(type(cluster_text), cluster_text)
            if cluster_text != protagonist:
                print()
                # deletes CLUSTER
        print('&&&&&&&&&&&&&')
        print("-------")
    break
