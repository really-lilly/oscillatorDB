import os
from pymongo import MongoClient
import warnings
from random import randrange
import tellurium as te
from random import randint

warnings.filterwarnings("ignore", category=DeprecationWarning)

# user: data
# pwd:  VuRWQ
astr = "mongodb+srv://data:VuRWQ@networks.wqx1t.mongodb.net"
client = MongoClient(astr)
database_names = client.list_database_names()
db = client['networks']
db = client.networks
collection = db['networks']
cur = collection.find({})

'''
CURRENT OPTIONS FOR modelType field:
"oscillator"
"random" - refers to random models used for controls

You can update this list here or use the add_model_type function. 
NOTE that this list is NOT attached to the database, so unless you push these changes, the database won't 'know'
about this list and what types of models it has.
'''
model_types = {"oscillator", "random"}

def get_model_types(printTypes=True):
    '''
    Get the current options for the modelType field
    :param printTypes: optional, boolean, prints the types if True
    :return: A set of possible model types (strings)
    '''
    return model_types



def generate_ID(n=19):
    '''
    Generate a random ID number that is not already in the database
    :param n: the number of digits in the ID
    :return: the ID number (string)
    '''
    ID = ''.join(["{}".format(randint(0, 9)) for num in range(0, 19)])
    _, length = query_database({"ID": ID}, returnLength=True, printSize=False)
    while length > 0:
        ID = ''.join(["{}".format(randint(0, 9)) for num in range(0, n)])
        _, length = query_database({"ID": ID}, returnLength=True, printSize=False)
    return ID


def is_valid_ant_string(antString):
    '''
    A basic test to assess if an antimony string is in the correct format for future processing
    :param antString: (str) antimony string to test
    :return: boolean, True if valid
    '''
    if antString.startswith('#'):
        antString = antString.split('\n')[1:]
    else:
        antString = antString.split('\n')
    if not (antString[0].startswith('var') or antString[0].startswith('ext')):
        raise Exception("Invalid antimony string: Species must be defined first using 'var' or 'ext'\n")
    k_tally = 0
    reaction_tally = 0
    for line in antString:
        if line.startswith("k"):
            k_tally += 1
        elif not (line.startswith("k") or line.startswith('var') or line.startswith('ext')):
            reaction_tally += 1
    if k_tally != reaction_tally:
        raise Exception("Invalid antimony string: the number of reactions and rate constants is not equal.\n")
    return True


def add_model(antString, modelType, ID=None, num_nodes=None, num_reactions=None, addReactionProbabilites=None,
              initialProbabilites=None, autocatalysisPresent=None, degredationPresent=None):
    '''
    Add a single new model to the database
    :param antString: (str) antimony string to be added
    :param modelType: (str) what type of model it is, eg. "oscillator"
    Optional args:
    :param ID: (str) model's ID
    :param num_nodes: (int) the number of species
    :param num_reactions: (int) the number of reactions
    :param addReactionProbabilites: int list, the probability of adding each reaction type:
        uni-uni, uni-bi, bi-uni, bi-bi
    :param initialProbabilites: int list, the initial probability of adding each reaction type when generating a
        random network: uni-uni, uni-bi, bi-uni, bi-bi
    :param autocatalysisPresent: boolean, True if there is an autocatalytic reaction
    :param degredationPresent: boolean, True if there is a degradation reaction
    :param analyzeReactions:
    '''
    if not is_valid_ant_string(antString):
        return
    if modelType not in model_types:
        raise Exception(f"'{modelType}' is not a valid modelType.\nDouble check spelling or add a new modelType with "
                        f"'add_model_type('{modelType}')'\n")
    _, length = query_database({"ID": ID}, returnLength=True, printSize=False)
    if length > 0: # Check if the ID is a duplicate
        raise Exception(f"Unable to add model. A model with the ID {ID} already exists.\n")
    if not ID:
        ID = generate_ID()
    if not num_nodes:
        num_nodes = get_nNodes(antString)
    if not num_reactions:
        num_reactions = get_nReactions(antString)
    modelDict = {'ID': ID,
                 'modelType': modelType,
                 'num_nodes': num_nodes,
                 'num_reactions': num_reactions,
                 'model': antString,
                 'addReactionProbabilities': addReactionProbabilites,
                 'initialProbabilities': initialProbabilites,
                 'Autocatalysis Present': autocatalysisPresent,
                 'Degredation Present': degredationPresent
                 }
    try:
        collection.insert_one(modelDict)
        print("Model successfully added")
    except:
        print("Something went wrong. Unable to add model.")


def print_entries(cursor=cur, n=None):
    '''
    Prints entries in the database
    :param n: optional, print out the first n entries. By default n is none and all entries are printed.
    :return: print out of every entry dictionary
    '''
    print(f"There are {cursor.count()} entries in the database")
    if not n:
        for doc in cursor:
            print(doc)
    else:
        count = 1
        for doc in cursor:
            print(doc)
            if count < n:
                count += 1
            else:
                break


def get_random_oscillator():
    result = query_database({'oscillator': True, 'num_nodes': 3})
    count = collection.count_documents({'oscillator': True, 'num_nodes': 3})
    return result[randrange(count)]


def get_nReactions(ant):
    '''
    Count how many reactions are in the model
    :param ant: antimony strings split by line, usually loaded with load_lines
    :return: integer, number of reactions
    '''
    # Takes a list of strings for each line in ant file
    nReactions = 0
    for line in ant:
        if '->' in line and not line.startswith('#'):
            if line.startswith('k'):
                break
            nReactions += 1
    return nReactions


def get_nNodes(ant):
    nNodes = 0
    # Skip the first line if it is a comment
    if ant[0].startswith('#'):
        ant = ant[1:]
    for line in ant:
        if line.startswith('var') or line.startswith('ext'):
            nNodes += 1
        else:
            break
    return nNodes


def query_database(query, returnLength=False, printSize=True):
    '''
    Retrieve all entries that match the query.
    :param query: A dictionary of the desired model traits
    returnLength: boolean, also returns the number of results if True
    printSize: boolean, prints number of results if True
    :return: A cursor object containing the dictionaries for all matching models
    '''
    length = collection.count_documents(query)
    if printSize:
        print(f'Found {length} matching entries.')
    if returnLength:
        return collection.find(query), length
    else:
        return collection.find(query)


def get_ids(query):
    '''
    Get the IDs of models that match the query
    :param query: A dictionary of model traits to look for
    :return: A list of IDs (str) for the matching models
    '''
    doc = collection.find(query)
    result = []
    for x in doc:
        result.append(x['ID'])
    if len(result) == 0:
        print('No entries found.')
        return None
    return result




def get_model_by_id(id):
    # If the id is provided as an integer, convert to string
    if isinstance(id, int):
        id = str(id)
    result = collection.find_one({'ID': id})
    if not result:
        print(f'Model {id} not found.')
    else:
        return result


def get_antimony(query):
    '''
    Get the antimony string(s) of models that match the query
    :param query: A dictionary of model traits to look for
    :return: If there is only a single matching model, returns the string for that model.
             Otherwise, returns a list of model strings.
    '''
    doc = collection.find(query)
    result = []
    for x in doc:
        result.append(x['model'])
    if len(result) == 0:
        print('No entries found.')
    elif len(result) == 1:
        return result[0]
    else:
        return result


def yes_or_no(question):
    '''
    Prompt the user to answer a yes or no question
    :param question: The question to be asked (str)
    :return: True if yes, False if no (boolean)
    '''
    answered = False
    while not answered:
        reply = str(input(question + ' (y/n): ')).lower().strip()
        if reply[0] == 'y':
            return True
        elif reply[0] == 'n':
            return False
        else:
            print('Please answer y or n.')


def get_sbml(query, sbml_path):
    id_list = get_ids(query)
    if not os.path.exists(sbml_path) or not os.path.isdir(sbml_path):
        os.mkdir(sbml_path)
    total = len(id_list)
    count = 0
    for id in id_list:
        try:
            ant = get_antimony({"ID": id})
            r = te.loada(ant)
            r.exportToSBML(f"{os.path.join(sbml_path, id)}.sbml")
            count += 1
        except:
            continue
    print(f"Exported {count} of {total} models to {sbml_path}")



def print_schema():
    # Print the schema for the database
    # as you can see, this method is a bit flawed in that it assumes this sample_model will have the maximum
    # number of schema
    sample_model = collection.find_one({"num_nodes": 3})
    for key in sample_model.keys():
        print(key)

def print_random_oscillator():
    result = query_database({"num_nodes":3, "oscillator": True})
    i = randrange(0, result.count())
    print(result[i]["model"])


def get_connection():
    '''
    Connect to the mongoDB
    :return: a MongoClient object connected to the database
    '''
    return MongoClient("mongodb+srv://data:VuRWQ@networks.wqx1t.mongodb.net")

get_connection()

