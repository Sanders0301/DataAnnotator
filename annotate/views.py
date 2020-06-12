import re
import json
import pickle
import random
import stringdist
import numpy as np

from django.http import HttpResponse
from django.shortcuts import render
from nltk import ngrams
from simstring.database.dict import DictDatabase
from simstring.measure.cosine import CosineMeasure
from simstring.searcher import Searcher
from simstring.feature_extractor.character_ngram import (
    CharacterNgramFeatureExtractor
)


def annotate_data(request):
    return render(request, 'annotate/annotate.html', {})


def suggest_cui(request):
    """
    Returns all relevant UMLS matches that have a cosine similarity
    value over the specified threshold, in descending order
    """

    global searcher

    if searcher is None:
        return HttpResponse('')

    selected_term = request.GET['selectedTerm']

    # Weight relevant UMLS matches based on word ordering
    weighted = {}
    for umls_match in searcher.ranked_search(selected_term, COSINE_THRESHOLD):
        umls_term = umls_match[1]
        # Add divsor to each term
        weighted[umls_term + ' :: UMLS ' + term_to_cui[umls_term] +
                 '***'] = stringdist.levenshtein(umls_term, selected_term)

    # Sort order matches will be displayed based on weights
    output = [i[0] for i in sorted(weighted.items(),
                                   key=lambda kv: kv[1])]

    # Remove divisor from final term
    if output != []:
        output[-1] = output[-1][:-3]

    return HttpResponse(output)


def setup_dictionary(request):
    """
    Setup user-specified ontolgoy to be used for
    automated mapping suggestions
    """

    global term_to_cui, searcher

    dictionary_selection = request.POST['dictionarySelection']
    if dictionary_selection == 'umlsDictionary':
        # searcher = umls_searcher
        pass
    elif dictionary_selection == 'noDictionary':
        # searcher = None
        pass
    elif dictionary_selection == 'userDictionary':
        json_data = json.loads(request.POST['dictionaryData'])
        db = DictDatabase(CharacterNgramFeatureExtractor(2))
        term_to_cui = {}
        for row in json_data:
            values = row.split('\t')
            if len(values) == 2:
                term_to_cui[values[1]] = values[0]
        for value in term_to_cui.keys():
            value = clean_dictionary_term(value)
            db.add(value)
        searcher = Searcher(db, CosineMeasure())
    return HttpResponse(None)


def clean_dictionary_term(value):
    return value.lower()


def get_annotated_texts(ann_files):
    """
    Get all annotated texts from ann_files (positive samples)
    """

    annotated = set()
    for ann_file in ann_files:
        annotations = ann_file.split('\n')
        for annotation in annotations:
            if len(annotation.strip()) > 0 and annotation[0] == 'T':
                raw_annotation_text = annotation.split('\t')[-1]
                # To-do: Existing annotations have spaces instead of underscore
                annotated.add(' '.join(raw_annotation_text.split('_')).lower().strip())
    return annotated


def get_unannotated_texts(txt_files, annotated):
    """
    Get all unannotated texts from txt_files (negative samples)
    """

    unannotated = set()
    for txt_file in txt_files:
        ngrams = get_ngram_data(txt_file)
        for ngram in ngrams:
            if ngram not in annotated:
                unannotated.add(ngram)
    return unannotated


def get_training_data(txt_files, ann_files, custom_dict=None):
    # Get all annotated texts from ann_files (positive samples)
    annotated = get_annotated_texts(ann_files)

    # Get all unannotated terms (negative samples)
    unannotated = get_unannotated_texts(txt_files, annotated)

    # To-do: Currently split to make equal length
    annotated_count = len(set(annotated))
    X = list(set(annotated)) + list(set(unannotated))[:annotated_count]
    y = [1 for _ in range(annotated_count)] + [0 for _ in range(annotated_count)]

    # Shuffle all data
    Xy = list(zip(X, y))
    random.shuffle(Xy)
    X, y = zip(*Xy)

    return X, y


def encode_training_data(X, y):
    global vectorizer
    X = vectorizer.fit_transform(X).toarray()
    return np.array(X), np.array(y)


def initialise_active_learner(request):
    global learner
    learner = pickle.load(open('prescription_model.pickle', 'rb'))
    return HttpResponse(None)


def get_annotation_suggestions(request):
    # global vectorizer

    txt_file = request.POST.get('txtFile')
    current_annotations = get_annotated_texts([request.POST.get('currentAnnotations')])

    # To-do: Improve sentence extraction
    newlines = txt_file.split('\n')
    sentences = []
    for newline in newlines:
        for sentence in newline.split('.'):
            sentence = sentence.strip()
            if sentence != '':
                sentences.append(sentence.strip())

    X = vectorizer.transform(sentences)

    predicted_labels = predict_labels(X)

    predicted_terms = []
    for i in range(len(predicted_labels)):
        if int(predicted_labels[i]) == 1:
            drug_name, drug_dose, drug_unit, drug_frequency = verify_prescription(sentences[i])
            if sentences[i] not in current_annotations and drug_name is not None:
                predicted_terms.append([sentences[i], drug_name, drug_dose, drug_unit, drug_frequency])

    return HttpResponse(json.dumps(predicted_terms))


def verify_prescription(sentence):
    has_drug = False
    has_dose = False
    has_unit = False
    has_frequency = False

    drug_name = ''
    drug_dose = ''
    drug_unit = ''
    drug_frequency = ''

    for token in sentence.split(' '):
        if has_number(token):
            has_dose = True
            drug_dose = re.findall(r'\d+', token)[0]

        if 'mg' in token:
            has_unit = True
            drug_unit = 'mg'

        if token == 'bd' or token == 'morning' or token == 'afternoon' or token == 'evening':
            has_frequency = True
            drug_frequency = token

    for drug in drugs:
        if drug in sentence.lower():
            has_drug = True
            drug_name = drug
            break

    if has_drug and has_dose and has_unit:
        return drug_name, drug_dose, drug_unit, drug_frequency
    else:
        return None, None, None, None


def has_number(token):
    return any(char.isdigit() for char in token)


def get_ngram_data(txt_file):
    """
    Get all possible ngrams from letter currently being annotated
    """

    potential_annotations = set()

    sentences = txt_file.split('\n')
    for sentence in sentences:
        if sentence.strip() == '':
            continue

        # Adjust n-gram range
        for n in range(5):
            for ngram in ngrams(sentence.split(' '), n):
                potential_annotation = ' '.join(ngram).lower().strip()

                if potential_annotation == '':
                    continue

                while potential_annotation[-1] in ('.', ',', '?', '!', ':'):
                    potential_annotation = potential_annotation[:-1]
                    if potential_annotation == '':
                        break

                if potential_annotation == '':
                    continue

                potential_annotation_words = potential_annotation.split(' ')
                stopword_count = 0
                for word in potential_annotation_words:
                    if word in stopwords:
                        stopword_count += 1
                if stopword_count == len(potential_annotation_words):
                    continue

                start_word_indx = 0
                for word_indx in range(len(potential_annotation_words)):
                    if potential_annotation_words[word_indx] in stopwords:
                        start_word_indx += 1
                    else:
                        break

                end_word_indx = len(potential_annotation_words)
                for word_indx in range(len(potential_annotation_words) - 1, -1, -1):
                    if potential_annotation_words[word_indx] in stopwords:
                        end_word_indx -= 1
                    else:
                        break

                potential_annotation = ' '.join(potential_annotation_words[start_word_indx:end_word_indx])

                if potential_annotation == '':
                    continue

                if potential_annotation.count('(') != potential_annotation.count(')'):
                    continue

                while potential_annotation[-1] in ('.', ',', '?', '!'):
                    potential_annotation = potential_annotation[:-1]

                if potential_annotation == '':
                    continue

                potential_annotations.add(potential_annotation)
    return potential_annotations


def query_active_learner(request):
    """
    Query n-gram data (have a category for unsure to help
    improve & category of confident labels)
    """

    global vectorizer, learner, query_X, query_idx

    txt_file = request.POST.get('txtFile')

    newlines = txt_file.split('\n')
    sentences = []
    for newline in newlines:
        for sentence in newline.split('.'):
            sentence = sentence.strip()
            if sentence != '':
                sentences.append(sentence)

    query_X = vectorizer.transform(sentences).toarray()
    query_idx, query_instance = learner.query(np.array(query_X))

    return HttpResponse(str(query_idx[0]) + '***' + list(sentences)[query_idx[0]])


def teach_active_learner(request):
    instance = request.POST.get('instance')
    label = request.POST.get('label')
    if instance:
        teach_active_learner_with_text(instance, label)
    else:
        teach_active_learner_without_text(label)
    return HttpResponse(None)


def teach_active_learner_without_text(label):
    global learner, query_X, query_idx
    learner.teach(query_X[query_idx], [label])


def teach_active_learner_with_text(instance, label):
    global learner, vectorizer
    data = np.array(vectorizer.transform([instance]).toarray())
    learner.teach(data, [label])


# Predict labels for n-gram data
def predict_labels(X):
    return learner.predict(X)


stopwords = set(open('stopwords.txt').read().split('\n'))
vectorizer = pickle.load(open('prescription_vect.pickle', 'rb'))
learner = None
COSINE_THRESHOLD = 0.7
query_X = None
query_idx = None
TEST = True

if TEST:
    term_to_cui = None
    db = None
    searcher = None
else:
    term_to_cui = pickle.load(open('term_to_cui.pickle', 'rb'))
    db = pickle.load(open('db.pickle', 'rb'))
    searcher = Searcher(db, CosineMeasure())

'''
def load_user_dictionary(request, data_file_path):
    try:
        chosen_file = gui.PopupGetFile('Choose a file', no_window=True)
    except:
        return HttpResponse(None)

    # Read in tab-delimited UMLS file in form of (CUI/tTERM)
    user_dict = open(chosen_file).read().split('\n')

    # Split tab-delimited UMLS file into seperate lists of cuis and terms
    cui_list = []
    term_list = []

    for row in user_dict:
        data = row.split('\t')
        if len(data) > 1:
            cui_list.append(data[0])
            term_list.append(data[1])

    global term_to_cui
    global db
    global searcher

    # Map cleaned UMLS term to its original
    term_to_cui = dict()

    for i in range(len(term_list)):
        term_to_cui[term_list[i]] = cui_list[i]

    # Create simstring model
    db = DictDatabase(CharacterNgramFeatureExtractor(2))

    for term in term_list:
        db.add(term)

    searcher = Searcher(db, CosineMeasure())
    return HttpResponse(None)

'''
drugs = ['lamotrigine', 'ferrous sulphate', 'carbamazepine', 'topiramate', 'sodium valproate', 'levetiracetam', 'bendroflumethiazide']