# data_utils.py
# @author: Lisa Wang
# @created:  2016
#
#===============================================================================
# DESCRIPTION: Code based on data_utils.py from loopy_nets project.
#===============================================================================
# CURRENT STATUS:
#===============================================================================
# USAGE: from data_utils import *
#

import os, struct
import numpy as np
from tflearn.data_utils import shuffle

from array import array as pyarray
from numpy import append, array, int8, uint8, zeros, int32, float32

import cPickle as pickle
from scipy.misc import imread

from sklearn.manifold import TSNE
from tflearn.data_utils import to_categorical, pad_sequences
from sklearn.metrics import accuracy_score
import matplotlib.pyplot as plt
from matplotlib import style

import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA

from collections import defaultdict

from constants import *


CIFAR10_DIR = '../data/cifar-10-batches-py'
CIFAR100_DIR = '../data/cifar-100-python'


EPSILON = 1e-8


def load_data(dataset='cifar10', num_training=50000, num_test=10000):
    print("Attempting to load dataset {} ...".format(dataset))
    X, Y, X_test, Y_test = None, None, None, None
    n_classes = 0
    if dataset == 'cifar10':
        X, Y, X_val, Y_val, X_test, Y_test = load_cifar(num_training=num_training, num_validation=0, num_test=num_test,
                                                    dataset='cifar10')
    elif dataset == 'cifar100_coarse':
        X, Y, X_val, Y_val, X_test, Y_test = load_cifar(num_training=num_training, num_validation=0, num_test=num_test,
                                                        dataset='cifar100')
        Y = Y[:,1]
        Y_test = Y_test[:,1]

    elif dataset == 'cifar100_fine':
        X, Y, X_val, Y_val, X_test, Y_test = load_cifar(num_training=num_training, num_validation=0, num_test=num_test,
                                                        dataset='cifar100')
        Y = Y[:, 0]
        Y_test = Y_test[:, 0]
    elif dataset == 'cifar100_joint_fine_only':
        X_train_joint, y_train_joint = load_data_pyramid(dataset="cifar100_joint", return_subset='joint_only')
        all_X = X_train_joint
        all_Y = y_train_joint[:, 0]  # extract only FINE... no coarse
        all_X, all_Y = shuffle(all_X, all_Y)

        testSplitIndex = int(len(all_X) * 0.85)
        X = all_X[:testSplitIndex]
        Y = all_Y[:testSplitIndex]
        X_test = all_X[testSplitIndex:]
        Y_test = all_Y[testSplitIndex:]
    else:
        print ("Dataset {} not found. ".format(dataset))
        sys.exit()
    n_classes = DATASET_TO_N_CLASSES[dataset]
    X, Y = shuffle(X, Y)
    Y = to_categorical(Y, n_classes)
    X_test, Y_test = shuffle(X_test, Y_test)
    Y_test = to_categorical(Y_test, n_classes)
    return X, Y, X_test, Y_test


def load_cifar100_prefeaturized():
    dataset_name = "cifar100_joint_prefeaturized"
    return pickle.load(open("../data/feature_sets/cifar100_joint_prefeaturized"))

def load_data_pyramid(dataset='cifar100_joint', return_subset='all'):
    if dataset == 'cifar100_joint':
        X_train_joint, y_train_joint, X_train_gate, y_train_gate, fine_or_coarse_train_gate, X_test, y_test, \
        fine_or_coarse_test = load_cifar_pyramid()
    elif dataset == 'cifar100_joint_prefeaturized':
        X_train_joint, y_train_joint, X_train_gate, y_train_gate, fine_or_coarse_train_gate, X_test, y_test, \
        fine_or_coarse_test = load_cifar100_prefeaturized()
    else:
        raise Exception("Dataset {} not found. ".format(dataset))

    if return_subset == 'all':
        return X_train_joint, y_train_joint, X_train_gate, y_train_gate, fine_or_coarse_train_gate, X_test, y_test, fine_or_coarse_test
    elif return_subset == 'joint_only':
        return X_train_joint, y_train_joint
    elif return_subset == 'gate_only':
        return X_train_gate, y_train_gate, fine_or_coarse_train_gate
    elif return_subset == 'test_only':
        return X_test, y_test, fine_or_coarse_test


#####################################################################################################################


def change_to_array(M, H, W):
    N = len(M[0])
    X = np.array(M[0], dtype=float32).reshape((N,1,H,W))
    y = np.array(M[1], dtype=int32)
    return X, y



def load_cifar(num_training=49000, num_validation=1000, num_test=10000, dataset='cifar10', normalize=True):
    """
    WARNING: Needs to be run from code directory, otherwise relative path
    will not work.
    Load the CIFAR-10 or CIFAR-100 dataset from disk.
    Returns train, validation and test sets.
    Note that num_training, num_validation and num_test have to be > 0.

    Important note for cifar100:
    Since cifar100 images have both fine labels (100) and coarse labels (20 superclasses),
    the returned y matrix has shape (num_samples, 2), where the first column corresponds to fine labels, and
    second column corresponds to coarse labels.
    Hence:
    y_fine = y[:,0]
    y_coarse = y[:,1]
    """
    # Load the raw CIFAR-10 data
    assert (dataset in ['cifar10', 'cifar100']), "dataset has to be either cifar10 or cifar100. "
    if dataset == 'cifar10':
        X_train, y_train, X_test, y_test = _load_cifar10(CIFAR10_DIR)
    elif dataset == 'cifar100':
        X_train, y_fine_train, y_coarse_train, X_test, y_fine_test, y_coarse_test = _load_cifar100(CIFAR100_DIR)
        y_train = np.stack((y_fine_train, y_coarse_train)).swapaxes(0,1)
        y_test = np.stack((y_fine_test, y_coarse_test)).swapaxes(0,1)

    mean_image = np.mean(X_train)
    std_deviation = np.mean(np.std(X_train, axis=0))
    print mean_image
    print std_deviation

    # Subsample the data
    mask = range(num_training, num_training + num_validation)
    X_val = X_train[mask]
    y_val = y_train[mask]
    mask = range(num_training)
    X_train = X_train[mask]
    y_train = y_train[mask]
    mask = range(num_test)
    X_test = X_test[mask]
    y_test = y_test[mask]

    if normalize:
        X_train -= mean_image
        X_val -= mean_image
        X_test -= mean_image

        X_train /= (std_deviation + EPSILON)
        X_val /= (std_deviation + EPSILON)
        X_test /= (std_deviation + EPSILON)


    return X_train, y_train, X_val, y_val, X_test, y_test



def load_cifar_train_test(dataset='cifar10'):
    """
    WARNING: Needs to be run from code directory, otherwise relative path
    will not work.
    Load the CIFAR-10 or CIFAR-100 dataset from disk.
    Returns train, validation and test sets.
    Note that num_training, num_validation and num_test have to be > 0.

    Important note for cifar100:
    Since cifar100 images have both fine labels (100) and coarse labels (20 superclasses),
    the returned y matrix has shape (num_samples, 2), where the first column corresponds to fine labels, and
    second column corresponds to coarse labels.
    Hence:
    y_fine = y[:,0]
    y_coarse = y[:,1]
    """
    # Load the raw CIFAR-10 data
    assert (dataset in ['cifar10', 'cifar100']), "dataset has to be either cifar10 or cifar100. "
    if dataset == 'cifar10':
        X_train, y_train, X_test, y_test = _load_cifar10(CIFAR10_DIR)
    elif dataset == 'cifar100':
        X_train, y_fine_train, y_coarse_train, X_test, y_fine_test, y_coarse_test = _load_cifar100(CIFAR100_DIR)
        y_train = np.stack((y_fine_train, y_coarse_train)).swapaxes(0,1)
        y_test = np.stack((y_fine_test, y_coarse_test)).swapaxes(0,1)

    return X_train, y_train, X_test, y_test



def load_cifar_pyramid():
    dataset = 'cifar100'
    X_train, y_train, X_test, y_test = load_cifar_train_test(dataset)

    coarse_to_fine_map = load_coarse_to_fine_map()

    fine_label_names, coarse_label_names = load_cifar100_label_names(label_type='all')
    fine_labels_joint = set()
    fine_labels_gate = set()
    fine_labels_only_test = set()

    for coarse_label, fine_labels in coarse_to_fine_map.iteritems():
        fine_labels_joint.update(set(fine_labels[:2]))
        fine_labels_gate.update(set(fine_labels[:4]))
        fine_labels_only_test.update(set(fine_labels[4]))

    X_train_joint, y_train_joint = [], []

    X_train_gate, y_train_gate = [], []

    fine_or_coarse_train_gate = [] # a 0 indicates it should predict fine, a 1 indicate it should predict coarse.

    for i in xrange(X_train.shape[0]):
        fine_label = fine_label_names[y_train[i, 0]]
        if fine_label in fine_labels_joint:
            X_train_joint.append(X_train[i])
            y_train_joint.append(y_train[i])
        if fine_label in fine_labels_gate:
            X_train_gate.append(X_train[i])
            y_train_gate.append(y_train[i])
            if fine_label in fine_labels_joint:
                fine_or_coarse_train_gate.append(0)
            else:
                fine_or_coarse_train_gate.append(1)

    X_train_joint = np.array(X_train_joint)
    y_train_joint = np.array(y_train_joint) # shape (num_samples, 2)

    X_train_gate = np.array(X_train_gate)
    y_train_gate = np.array(y_train_gate) # shape (num_samples, 2)
    fine_or_coarse_train_gate = np.array(fine_or_coarse_train_gate)
    # print fine_or_coarse_train_gate.shape
    fine_or_coarse_test = []

    for i in xrange(X_test.shape[0]):
        fine_label = y_test[i,0]
        if fine_label in fine_labels_joint: # if label of current sample is one of the fine classes we trained on.
            fine_or_coarse_test.append(0)
        else:
            fine_or_coarse_test.append(1)

    fine_or_coarse_test = np.array(fine_or_coarse_test)

    return X_train_joint, y_train_joint, X_train_gate, y_train_gate, fine_or_coarse_train_gate, X_test, y_test, fine_or_coarse_test


def _load_cifar100(ROOT):
    Xtr, Y_fine_tr, Y_coarse_tr = _load_cifar100_batch(os.path.join(ROOT, 'train'))
    Xte, Y_fine_te, Y_coarse_te  = _load_cifar100_batch(os.path.join(ROOT, 'test'))
    return Xtr, Y_fine_tr, Y_coarse_tr, Xte, Y_fine_te, Y_coarse_te


def _load_cifar100_batch(filename):
    with open(filename, 'rb') as f:
        datadict = pickle.load(f)
        batch_label = datadict['batch_label']
        print ("loading cifar batch {}".format(batch_label))
        X = datadict['data']
        Y_fine = datadict['fine_labels']
        Y_coarse = datadict['coarse_labels']

        num_samples = 0
        if batch_label == 'training batch 1 of 1':
            num_samples = 50000

        elif batch_label == 'testing batch 1 of 1':
            num_samples = 10000
        X = X.reshape(num_samples, 3, 32, 32).transpose(0, 2, 3, 1).astype("float")
        Y_fine = np.array(Y_fine)
        Y_coarse = np.array(Y_coarse)
        return X, Y_fine, Y_coarse


def _load_cifar10(ROOT):
    """ load all of cifar, adapted from CS231N assignment 1 """
    xs = []
    ys = []
    for b in range(1,6):
        f = os.path.join(ROOT, 'data_batch_%d' % (b, ))
        X, Y = _load_cifar10_batch(f)
        xs.append(X)
        ys.append(Y)
    Xtr = np.concatenate(xs)
    Ytr = np.concatenate(ys)
    del X, Y
    Xte, Yte = _load_cifar10_batch(os.path.join(ROOT, 'test_batch'))
    return Xtr, Ytr, Xte, Yte


def _load_cifar10_batch(filename):
    """ load single batch of cifar, adapted from CS231N assignment 1"""
    with open(filename, 'rb') as f:
        datadict = pickle.load(f)
        batch_label = datadict['batch_label']
        print ("loading cifar batch {}".format(batch_label))
        X = datadict['data']
        Y = datadict['labels']
        X = X.reshape(10000, 3, 32, 32).transpose(0,2,3,1).astype("float")
        Y = np.array(Y)
        return X, Y


def load_cifar10_label_names():
    filename = os.path.join(CIFAR10_DIR, 'batches.meta')
    with open(filename, 'rb') as f:
        datadict = pickle.load(f)
        label_names = datadict['label_names']
        return label_names


def load_cifar100_label_names(label_type='all'):
    """
    label_type:
        'all': returns both fine and coarse labels
        'fine': return only fine labels
        'coarse': return only coarse labels
    """
    filename = os.path.join(CIFAR100_DIR, 'meta')
    with open(filename, 'rb') as f:
        datadict = pickle.load(f)
        fine_label_names = datadict['fine_label_names']
        coarse_label_names = datadict['coarse_label_names']
        if label_type == 'all':
            return fine_label_names, coarse_label_names
        elif label_type == 'fine':
            return fine_label_names
        elif label_type == 'coarse':
            return coarse_label_names


def load_coarse_to_fine_map():
    coarse_to_fine_map = pickle.load(open('coarse_to_fine_map.pickle', 'rb+'))
    return coarse_to_fine_map


def create_coarse_to_fine_map():
    coarse_to_fine_map = defaultdict(set)
    X_train, y_train, X_test, y_test = load_cifar_train_test(dataset='cifar100')
    fine_label_names, coarse_label_names = load_cifar100_label_names(label_type='all')

    fine_y_train = y_train[:, 0]
    coarse_y_train = y_train[:, 1]

    for i in xrange(y_train.shape[0]):
        coarse_label = coarse_label_names[coarse_y_train[i]]
        fine_label = fine_label_names[fine_y_train[i]]

        if fine_label not in coarse_to_fine_map[coarse_label]:
            coarse_to_fine_map[coarse_label].add(fine_label)

    for k in coarse_to_fine_map:
        coarse_to_fine_map[k] = sorted(list(coarse_to_fine_map[k]))

    print coarse_to_fine_map
    pickle.dump(coarse_to_fine_map, open('coarse_to_fine_map.pickle', 'wb+'))
    return coarse_to_fine_map





if __name__=='__main__':
    # X_train, y_train, X_val, y_val, X_test, y_test = load_cifar(num_training=49000, num_validation=1, num_test=1000, dataset='cifar10')
    # print 'X_train shape: {}'.format(X_train.shape)
    # print 'y_train shape: {}'.format(y_train.shape)
    # print 'X_val shape: {}'.format(X_val.shape)
    # print 'X_test shape: {}'.format(X_test.shape)
    #
    # X_train, y_train, X_val, y_val, X_test, y_test = load_cifar(num_training=50000, num_validation=0, num_test=10000,
    #                                                             dataset='cifar100')
    # print 'X_train shape: {}'.format(X_train.shape)
    # print 'y_train shape: {}'.format(y_train.shape)
    # print 'X_val shape: {}'.format(X_val.shape)
    # print 'X_test shape: {}'.format(X_test.shape)
    #
    # label_names = load_cifar10_label_names()
    # print label_names
    # fine_label_names, coarse_label_names = load_cifar100_label_names()
    # print fine_label_names
    # print coarse_label_names


    coarse_to_fine_map = create_coarse_to_fine_map()