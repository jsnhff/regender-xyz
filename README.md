# Regender Books

ToC:
1. [Initial Set-up & Installation](#initial-setup)
2. [How to run](#run)<br>
   a. [config.ini](#config)<br>
   b. [reflect config.ini changes in the code](#code-changes)
3. [Approach](#approach)
3. [Analysing a new piece of text](#continuing-work)
4. [Progress - a.k.a What's been analysed so far](#progress)
5. [Project Management](#management)
4. [Libraries Used](#libraries)
5. [Resources and References](#resources-and-references)

---


### Initial Set-up & Installation <a name="initial-setup"></a>

1. Install the needed OS- and python- packages

```sh
python3 requirements.txt # installs all Python-related dependencies
sh requirements.sh # installs GIT on Linux/MAC

git --version # check if you have git isntalled
> git version 2.XX.XX # OUTPUT if git is installed.If not, type in
```


2. Clone the git repo on your local machine by either:
- downloading the `.zip` folder of the repo from [here](https://github.com/estambolieva/regendered-books/archive/master.zip) and decompressing it in a location of your choice on your machine, OR
- opening up the terminal, and using `git` - clone the project:

```sh

git clone https://github.com/estambolieva/regendered-books.git
```


3. Create a virtual environment on which to work on (in terminal) & install all needed packages

In the root folder of the project - create a virtual environment to use when working on the projects - on which we install all needed packages

```sh
python3 -m venv nlp # creates the virtual enviornment
```

a. every time you work on the project, activate this virtual environment as the first step after opening the terminal. 

```sh
souce nlp/bin/activate
```

Before I activate the virtual environment, my terminal window prompt looks something like this: `katia@katias-laptop`, and like this - `(nlp)katia@katias-laptop` - after I activate the environment. The `(nlp)` shows me  that the environment has been activated :+1:.  

**Only once**, install all required pythong packages needed by executing

```sh
pip3 install -r requrements.txt # install app Python dependencies (needed packages)
```

4. Install NeuralCoref from core & the correct associated version of Spacy with it

```sh
pip uninstall neuralcoref
git clone https://github.com/huggingface/neuralcoref.git
cd neuralcoref
pip install -r requirements.txt
pip install -e .
pip uninstall spacy
pip install spacy
python -m spacy download en
```

test it quickly (if you'd like) in a Python console to ensure that it works as expected:

```py
import spacy
nlp = spacy.load('en')
import neuralcoref      ## ignore RuntimeWarning(s)
neuralcoref.add_to_pipe(nlp)
doc = nlp(u'My sister has a dog. She loves him.')
doc._.has_coref         ## True
doc._.coref_clusters    ## [My sister: [My sister, She], a dog: [a dog, him]]
doc._.coref_resolved    ## 'My sister has a dog. My sister loves a dog.'
```

Link with installation insturctuons found [here](https://github.com/huggingface/neuralcoref)


## How to run <a name="run"></a>

The main files which needs to be run in names `coreference_resolution.py` located in the `code` folder. To execute it, run:

```sh
python3 code/coreference_resoluton.py
```

Note: make sure you are running this from the root folder of the git project if you want to use the 1-liner above ⬆️. 


### a. config.ini <a name="config"></a>

Every time we start working with a new piece of text - we need to update the `config.ini` file. It is located in the root folder of the project. Hint - you can install [Sublime Text](https://www.sublimetext.com/) editor to edit it if you are wondering how to open it. 

This is how it works for now -> whenever we start working with a new text, we create the following entry for it in the `config.ini` file:

![Config.ini for Rabbit Angstrom: Rabbit, Run](https://github.com/estambolieva/regendered-books/raw/master/imgs/rabbit_config_ini.png)

- `[__BOOK_NAME__]` is the marker used by Python to tell the rest of the code where to look for the replacement strings we introduce for each text/book in this file. **Note**: Currently we use the name of the book as the marker - e.g. when we work on Beloved, we set this marker to `[rabbitrun]` (`__BOOK_NAME__` = `rabbitrun`). 
- `TEXT_FILE` - currently: pointing either to an Excel file with the experimental exceprts of books - pushed to the github repo OR alink to Harry Potter's Google doc on Gdrive; `future`: this can be any link - AWS S3, etc. 
- `TEXT_FILE_SHEET` - either `None` (for Harry Potter) OR `Sheet1` which is the name of the only sheet in the Github repo Excel file 
- `SHEET_LINE` - either `None` (for Harry Potter) OR an integer indicating the line in `Sheet1` in the Github repo Excel file, on which the book exceprt's info is stored at
- `PROTAGONIST_REPLACEMENT_NAME` is the name we give to the protagonist who we regender, e.g. from `Sethe` to `Michael` in the context of `Beloved`
- `OTHER_CHARACTER_SAME_NAME_CHANGE` - we define this in case there is another `Michael` mentioned somewhere in the text - we do not want our renamed proganist's name to clash with the name of another character. **Note** - we developed this for `Pride & Prejudice` - a text in which we regendered `Mrs. Bennet` and changed her name to `Mr. Bennet` - which happens to be the name of her husband. `OTHER_CHARACTER_SAME_NAME_CHANGE` in this case is set to `the other Mr. Bennet`.
- `CHARACTER_1` - we list the name of another very prominent character in the text/book, whose name might cause coreference problems. ❗ **Important** - work in progress, this logic has not been fully developed yet.


### b. reflect config.ini changes in the code <a name="code-changes"></a>



---

## Project Management <a name="management"></a>

We use Trello for task management - here is the link to [our Trello board](https://trello.com/b/WlGnaGox/regender-alpha)
- ask the admin (Jason Huff) to add you to it


We use Google Docs to document our experiments in detail (e.g. human-readable documentation) - here is the [link](https://drive.google.com/drive/u/0/folders/14XVle1QEer1k527lhCYV376f5qxTpUUY) to it
- ask the admin (Jason Huff) to grant access to you


We use Github as our code repository. 


---

## Libraries <a name="libraries"></a>

- [Spacy](https://spacy.io/) - as a general NLP tool
- [Neuralcoref](https://github.com/huggingface/neuralcoref) with Spacy - for coreference resolution
- [xlrd](https://pypi.org/project/xlrd/) - to read experiment's data from Excel sheets

---

## Resources and References <a name="resources-and-references"></a>

1. [NeuralCoref Universe](https://spacy.io/universe/project/neuralcoref) & Documentation in the for of [README.md](https://github.com/huggingface/neuralcoref)
2. [NeuralCoref Visualizer](https://spacy.io/universe/project/neuralcoref-vizualizer)
3. [NeuralCoref Source Code on Github](https://github.com/huggingface/neuralcoref)
4. [blog post: Coreference resolution using Spacy](https://www.rangakrish.com/index.php/2019/02/03/coreference-resolution-using-spacy/)