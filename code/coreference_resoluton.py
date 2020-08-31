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
doc = nlp(protagonist)
print('--------')
found_entities = doc.ents != ()
if found_entities:
    for ent in doc.ents:
        print(ent.text, ent.start_char, ent.end_char, ent.label_)
    print('--------')
else:
    ruler.add_patterns([{"label": "PERSON", "pattern": protagonist}])
    nlp.add_pipe(ruler)
    doc = nlp(protagonist)
    for ent in doc.ents:
        print(ent.text, ent.start_char, ent.end_char, ent.label_)
