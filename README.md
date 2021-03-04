# regender.xyz

## Table of Contents
1. [Initial Setup & Installation](#initial-setup)
2. [Running the Software](#run)<br>
   a. [config.ini](#config)<br>
   b. [reflect config.ini changes in the code](#code-changes)
3. [Approach](#approach)
4. [Analysing a new piece of text](#continuing-work)
5. [Progress - a.k.a What's been analysed so far](#progress)
6. [Project Management](#management)
7. [Libraries Used](#libraries)
8. [Resources and References](#resources-and-references)

---

### Initial Setup & Installation <a name="initial-setup"></a>

1. Open your terminal and get ready to use the command line for all the following steps 👾

2. Install the required libraries: Neuralcoref & spaCy 📚

First let's uninstall any existing copies of Neuralcoref

```sh
pip3 uninstall neuralcoref
```
Next, we'll use Git to clone the Neuralcoref repository and setup spaCy

```sh
git clone https://github.com/huggingface/neuralcoref.git
cd neuralcoref
pip3 install -r requirements.txt
pip3 install -e .
pip3 uninstall spacy
pip3 install spacy==2.3.2 # This version is copmatible with neuralcoref
```
Finally, we'll use python3 to download the latest english data model.

```sh
python3 -m spacy download en
```

Great. The Neuralcoref and spaCy libraries are installed. Switch back to you root folder to get ready to setup the main regender-xyz software.

```sh
cd
```

3. Use Git to clone the regender-xyz repository to your local machine 💾

```sh
git clone https://github.com/jsnhff/regendered-xyz.git
```

*Alternatively you can [download the `.zip` folder of the repository](https://github.com/jsnhff/*regendered-xyz/archive/master.zip) and decompressing it in a location of your choice on your machine.*

4. Install the required OS and Python packages 📦

Move into the regneder-xyz directory.
```sh
cd regender-xyz
```

**Start by installing all Python-related dependencies for the project.**
You might see some 'WARNING' messages about script locations if your system has some of the required scrips already installed on your machine. You can ingore these or surpress them by appending --no-warn-script-location to the line below.

```sh
pip3 install --user --upgrade --force-reinstall -r requirements.txt
```
*If you haven't installed pip you can find instructions [here](https://pip.pypa.io/en/stable/installing/)*

**Update your systems packages and check for the latest installed version of Git**
Katia created this helpful script.
```sh
sh requirements.sh
```
*Note: Right now this script only works for Linux and Mac systems. If it doesn't work for you please manually make sure your system is up-to-date, including git.*


5. Create a virtual environment for your work (do the libraries for neuralcoref and spaCy need to be installed after the virtual environment is activated?)

In the root folder of the project "[user]/regender-xyz" create a virtual environment to use when working on the project. We'll install all the needed packages into this folder.

```sh
python3 -m venv nlp
```
*This might take a second or two to complete.*


**Activate your new virtual environment.**
You'll need to do this each time you want to work on a regendering project.

```sh
source nlp/bin/activate
```

*You will know you've successfully activated the virtual environment when `(nlp)` appears at the beginning of your terminal's prompt. It will look something like this `(nlp)katia@katias-laptop`.*

6. Test it quickly (if you'd like) in a Python console to ensure that it works as expected:

First activate your virtual environment.
```sh
source nlp/bin/activate
```
Next open an Python console.
```py
python3
```

Test the script. We recommend pasting it line by line to catch errors and see results as each line runs.
```py
import spacy
nlp = spacy.load('en')
import neuralcoref      ## ignore RuntimeWarning(s)
neuralcoref.add_to_pipe(nlp)
doc = nlp(u'My sister has a dog. She loves him.')
doc._.has_coref         ## True
doc._.coref_clusters    ## [My sister: [My sister, She], a dog: [a dog, him]]
doc._.coref_resolved    ## 'My sister has a dog. My sister loves a dog.'

exit()
```

Link with installation insturctuons found [here](https://github.com/huggingface/neuralcoref)

To leave the virtual environment type...
```sh
deactivate
```

## Running the Software <a name="run"></a>

The main files which needs to be run in names `regender_main.py` located in the `code` folder. To execute it, run the command below from the root git folder:

```sh
python3 code/regender_main.py
```

**Note**: Make sure you are running this from the root folder of the git project if you want to use the 1-liner above ⬆️ as is.


This will execute the `regendering` logic to the selected text. Let's chat about how to select the text to regender.


### Select Text to Regender

This step consists of two sub-steps:
- update the `config.ini` file in which we keep fixed variables we need when regendering any given text
- update the code to point which text is being regendered on the current run
- (optional) update the code to select that to print as intermediate steps


#### a. Update config.ini <a name="config"></a>

Every time we start working with a new piece of text - we need to update the `config.ini` file. It is located in the root folder of the project. Hint - you can install [Sublime Text](https://www.sublimetext.com/) editor to edit it if you are wondering how to open it. 

This is how it works for now -> whenever we start working with a new text, we create the following entry (if non-existent) for it in the `config.ini` file:

![Config.ini for Rabbit Angstrom: Rabbit, Run](https://github.com/estambolieva/regendered-books/raw/master/imgs/rabbit_config_ini.png)

- `[__BOOK_NAME__]` is the marker used by Python to tell the rest of the code where to look for the replacement strings we introduce for each text/book in this file. **Note**: Currently we use the name of the book as the marker - e.g. when we work on Beloved, we set this marker to `[rabbitrun]` (`__BOOK_NAME__` = `rabbitrun`). 
- `TEXT_FILE` - currently: pointing either to an Excel file with the experimental exceprts of books - pushed to the github repo OR alink to Harry Potter's Google doc on Gdrive; `future`: this can be any link - AWS S3, etc. 
- `TEXT_FILE_SHEET` - either `None` (for Harry Potter) OR `Sheet1` which is the name of the only sheet in the Github repo Excel file 
- `SHEET_LINE` - either `None` (for Harry Potter) OR an integer indicating the line in `Sheet1` in the Github repo Excel file, on which the book exceprt's info is stored at
- `PROTAGONIST_REPLACEMENT_NAME` is the name we give to the protagonist who we regender, e.g. from `Sethe` to `Michael` in the context of `Beloved`
- `OTHER_CHARACTER_SAME_NAME_CHANGE` - we define this in case there is another `Michael` mentioned somewhere in the text - we do not want our renamed proganist's name to clash with the name of another character. **Note** - we developed this for `Pride & Prejudice` - a text in which we regendered `Mrs. Bennet` and changed her name to `Mr. Bennet` - which happens to be the name of her husband. `OTHER_CHARACTER_SAME_NAME_CHANGE` in this case is set to `the other Mr. Bennet`.
- `CHARACTER_1` - we list the name of another very prominent character in the text/book, whose name might cause coreference problems. ❗ **Important** - work in progress, this logic has not been fully developed yet.


The `config.ini` file is ready to support the rengendering of a new piece of text. 


**Notable Mention**

One-time Gdrive Authentication

`The authentication flow has completed. You may close this window.`


#### b. reflect config.ini changes in the code <a name="code-changes"></a>


We need make 1 change in the code in the file `regender_main.py` in the `code` folder.

We need to copy the string (`text_id`) which we have defined in `config.ini` and replace what is shown highlighted in `regender_main.py`  the image below.

![Change the code](https://github.com/estambolieva/regendered-books/raw/master/imgs/change_coreference_resolution_py.png)

When this is done, we are ready to regender. Run:

```sh
python3 code/regender_main.py
```

The regendered text is written in a file in the `output` folder (no worries, the `requirements.sh` script you ran when doing the installation and setup has already created it in the root git folder) with a name which consists of:
- the `text_id` or the name of the book the way we have written it in the `config.ini` file
- `_regendered.txt`.


#### c. (optional) update the code to select that to print as intermediate steps

---

## Project Management <a name="management"></a>

We use Trello for task management - here is the link to [our Trello board](https://trello.com/b/WlGnaGox/regender-alpha)
- ask the admin (Jason Huff) to add you to it


We use Google Docs to document our experiments in detail (e.g. human-readable documentation) - here is the [link](https://drive.google.com/drive/u/0/folders/14XVle1QEer1k527lhCYV376f5qxTpUUY) to it
- ask the admin (Jason Huff) to grant access to you


We use Github as our code repository. 


---

## Libraries <a name="libraries"></a>

- [Spacy](https://spacy.io/) - As a general NLP tool
- [Neuralcoref](https://github.com/huggingface/neuralcoref) with Spacy - for coreference resolution
- [xlrd](https://pypi.org/project/xlrd/) - to read experiment's data from Excel sheets

---

## Resources and References <a name="resources-and-references"></a>

1. [NeuralCoref Universe](https://spacy.io/universe/project/neuralcoref) & Documentation in the for of [README.md](https://github.com/huggingface/neuralcoref)
2. [NeuralCoref Visualizer](https://spacy.io/universe/project/neuralcoref-vizualizer)
3. [NeuralCoref Source Code on Github](https://github.com/huggingface/neuralcoref)
4. [blog post: Coreference resolution using Spacy](https://www.rangakrish.com/index.php/2019/02/03/coreference-resolution-using-spacy/)
