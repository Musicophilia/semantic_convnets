# -*- coding: utf-8 -*-

# pipeline.py
# @author: Lisa Wang
# @created: Nov 12 2016
#
#===============================================================================
# DESCRIPTION:
#
# Exports train and test functions for all network models and data sets.
# Can be run from the command line.
#===============================================================================
# CURRENT STATUS: Working
#===============================================================================
# USAGE:
# In another python script:
# from pipeline import *
#
# Commandline:
# python pipeline.py -t <train_or_test_mode> -m <model_id> -d <dataset>
# or to get help:python pipeline.py -h
#
#===============================================================================

from __future__ import division, print_function, absolute_import

import os, sys, getopt
import datetime

import tensorflow as tf
import tflearn
from tflearn.data_utils import shuffle, to_categorical
from sklearn.metrics import accuracy_score
import numpy as np

from utils import *
from data_utils import *

sys.path.append("../") # so we can import models.
from models import *
#===============================================================================

DATASET_TO_N_CLASSES = {
    'cifar10' : 10,
    'cifar100_coarse': 20,
    'cifar100_fine': 100
}


ALL_MODEL_DICTS = {
    'simple_cnn': {'network_type': 'simple_cnn', 'dataset': 'cifar10'},
    'simple_cnn_cifar100_joint': {'network_type': 'simple_cnn', 'dataset': None},  # TODO joint
    'simple_cnn_cifar100_coarse': {'network_type': 'simple_cnn', 'dataset': 'cifar100_coarse'},
    'simple_cnn_cifar100_fine': {'network_type': 'simple_cnn', 'dataset': 'cifar100_fine'},
    'simple_cnn_extended1_cifar100_fine': {'network_type': 'simple_cnn_extended1', 'dataset': 'cifar100_fine'},

    'lenet_cnn_cifar100_coarse': {'network_type': 'lenet_cnn', 'dataset': 'cifar100_coarse'},
    'vggnet_cnn_cifar100_coarse': {'network_type': 'vggnet_cnn', 'dataset': 'cifar100_coarse'},

    'lenet_cnn_cifar100_fine': {'network_type': 'lenet_cnn', 'dataset': 'cifar100_fine'},
    'vggnet_cnn_cifar100_fine': {'network_type': 'vggnet_cnn', 'dataset': 'cifar100_fine'},

    'pyramid_cifar100': {'network_type': 'pyramid', 'dataset': 'cifar100_joint'}
}

def get_weights_to_preload_function(model_id, checkpoint_model_id, is_training):
    def variable_name_map_func(existing_var_op_name):
        if not is_training:  # In test, always preload ALL weights
            return existing_var_op_name
        if checkpoint_model_id == model_id:  # If we're preloading the same model, then obviously preload ALL weights!
            return existing_var_op_name

        # Otherwise, we're in training and we can simply
        print(existing_var_op_name)
        if 'unique' in existing_var_op_name:
            return None
        else:
            return existing_var_op_name

    return variable_name_map_func

def load_model(model_id, n_classes=10, pyramid_output_dims=None, is_training=False, checkpoint_model_id=None, get_hidden_reps=False):
    # should be used for all models

    assert (is_training ^ get_hidden_reps), "If you train, you can't get hidden reps and vice versa. "
    print ('Loading model...')

    model_dict = ALL_MODEL_DICTS[model_id]
    network_type = model_dict['network_type']

    tensorboard_dir = '../tensorboard_logs/' + model_id + '/'
    checkpoint_path = '../checkpoints/' + model_id + '/'
    best_checkpoint_path = '../best_checkpoints/' + model_id + '/'

    print (tensorboard_dir)
    print (checkpoint_path)
    print (best_checkpoint_path)

    check_if_path_exists_or_create(tensorboard_dir)
    check_if_path_exists_or_create(checkpoint_path)
    check_if_path_exists_or_create(best_checkpoint_path)

    network = load_network(network_type=network_type, n_classes=n_classes, pyramid_output_dims=pyramid_output_dims,
                           get_hidden_reps=get_hidden_reps)

    if is_training:
        model = tflearn.DNN(network, tensorboard_verbose=2, tensorboard_dir=tensorboard_dir,
                            checkpoint_path=checkpoint_path, best_checkpoint_path=best_checkpoint_path, max_checkpoints=3)
    else:
        model = tflearn.DNN(network)

    if checkpoint_model_id:
        start_checkpoint_path = '../checkpoints/' + checkpoint_model_id + '/'
        checkpoint = tf.train.latest_checkpoint(start_checkpoint_path)  # can be none of no checkpoint exists
        if checkpoint and os.path.isfile(checkpoint):
            variable_name_map_func = get_weights_to_preload_function(model_id, checkpoint_model_id, is_training)
            model.load(checkpoint, weights_only=True, verbose=True, variable_name_map=variable_name_map_func)
            # model.load(checkpoint, verbose=True)
            print('Checkpoint loaded.')
        else:
            print('No checkpoint found. ')

    print ('Model loaded.')
    return model


def load_network(network_type='simple_cnn', n_classes=10, pyramid_output_dims=None, get_hidden_reps=False):
    network = None

    if network_type == 'simple_cnn':
        network = simple_cnn.build_network([n_classes], get_hidden_reps=get_hidden_reps)
    elif network_type == 'lenet_cnn':
        network = lenet_cnn.build_network([n_classes])
    elif network_type == 'lenet_small_cnn':
        network = lenet_small_cnn.build_network([n_classes])
    elif network_type == 'vggnet_cnn':
        network = vggnet_cnn.build_network([n_classes])
    elif network_type == 'simple_cnn_extended1':
        network = simple_cnn_extended1.build_network([n_classes], get_hidden_reps=get_hidden_reps)
    elif network_type == 'pyramid':
        network = joint_pyramid_cnn.build_network(pyramid_output_dims, get_hidden_reps=get_hidden_reps)
    else:
        print("Model {} not found. ".format(network_type))
        sys.exit()
    return network


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

    else:
        print ("Dataset {} not found. ".format(dataset))
        sys.exit()
    n_classes = DATASET_TO_N_CLASSES[dataset]
    X, Y = shuffle(X, Y)
    Y = to_categorical(Y, n_classes)
    X_test, Y_test = shuffle(X_test, Y_test)
    Y_test = to_categorical(Y_test, n_classes)
    return X, Y, X_test, Y_test


def load_data_pyramid(dataset='cifar100_joint', return_subset='all'):
    if dataset == 'cifar100_joint':
        X_train_joint, y_train_joint, X_train_gate, y_train_gate, fine_or_coarse_train_gate, X_test, y_test, \
        fine_or_coarse_test = load_cifar_pyramid()
    else:
        print("Dataset {} not found. ".format(dataset))
    if return_subset == 'all':
        return X_train_joint, y_train_joint, X_train_gate, y_train_gate, fine_or_coarse_train_gate, X_test, y_test, fine_or_coarse_test
    elif return_subset == 'joint_only':
        return X_train_joint, y_train_joint
    elif return_subset == 'gate_only':
        return X_train_gate, y_train_gate, fine_or_coarse_train_gate
    elif return_subset == 'test_only':
        return X_test, y_test, fine_or_coarse_test


def train_model(model_id='simple_cnn', dataset='cifar10', checkpoint_model_id=None):

    print ("Training model {} with dataset {}".format(model_id, dataset))

    n_classes = DATASET_TO_N_CLASSES[dataset]

    date_time_string = datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    run_id = "{}_{}".format(model_id, date_time_string)
    # Train using classifier
    model = load_model(model_id=model_id, n_classes=n_classes, is_training=True, checkpoint_model_id=checkpoint_model_id)

    X, Y, X_test, Y_test = load_data(dataset)

    model.fit(X, Y, n_epoch=50, shuffle=True, validation_set=0.1,
              show_metric=True, batch_size=128, run_id=run_id, snapshot_step=100)


def train_pyramid_model(model_id='pyramid_cifar100', dataset='cifar100_joint',  checkpoint_model_id=None):
    coarse_dim = 20
    fine_dim = 100
    X_train_joint, y_train_joint = load_data_pyramid(dataset=dataset, return_subset='joint_only')

    X_train_joint, y_train_joint = shuffle(X_train_joint, y_train_joint)
    y_train_fine, y_train_coarse = y_train_joint[:, 0], y_train_joint[:, 1]
    y_train_fine, y_train_coarse = to_categorical(y_train_fine, fine_dim), to_categorical(y_train_coarse, coarse_dim)

    y_train_joint = np.concatenate((y_train_coarse, y_train_fine), axis=1)

    model = load_model(model_id, pyramid_output_dims=[coarse_dim, fine_dim], is_training=True, checkpoint_model_id=checkpoint_model_id)

    date_time_string = datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    run_id = "{}_{}".format(model_id, date_time_string)

    model.fit(X_train_joint, y_train_joint, n_epoch=50, shuffle=True, validation_set=0.1,
              show_metric=True, batch_size=128, run_id=run_id, snapshot_step=100)


def test_model(model_id='simple_cnn', dataset='cifar10'):
    print("Testing model {} with dataset {}".format(model_id, dataset))

    X, Y, X_test, Y_test = load_data(dataset)
    n_classes = DATASET_TO_N_CLASSES[dataset]

    # Test using classifier
    model = load_model(model_id, n_classes=n_classes, checkpoint_model_id=model_id, is_training=False)
    # pred_train_probs = model.predict(X)
    # pred_train = np.argmax(pred_train_probs, axis=1)
    # train_acc = accuracy_score(pred_train, np.argmax(Y, axis=1))
    pred_test_probs = model.predict(X_test)
    pred_test = np.argmax(pred_test_probs, axis=1)
    test_acc = accuracy_score(pred_test, np.argmax(Y_test, axis=1))
    print("Test acc: {}".format( test_acc))
    # print("Train acc: {}\t Test acc: {}".format(train_acc, test_acc))


def read_commandline_args():
    def usage():
        print("Usage: python pipeline.py -t <train_or_test_mode> -m <model_id> -c <ckpt_model_id>")
    try:
        opts, args = getopt.getopt(sys.argv[1:],"ht:m:d:c:", ["help", "train_or_test_mode", "model_id", "ckpt_model_id"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print (str(err))  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    mode, model_id, checkpoint_model_id = None, None, None
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-t", "--train_or_test_mode"):
            mode = a
        elif o in ("-m", "--model_id"):
            model_id = a
        elif o in ("-c", "--ckpt_model_id"):
            checkpoint_model_id = a
        else:
            assert False, "unhandled option"

    if mode == None:
        mode = 'train'
        print ("Using default mode: train. To test, please specify with commandline arg '-t test ")

    if model_id == None:
        model_id = 'simple_cnn'


    return mode, model_id, checkpoint_model_id


def main():
    mode, model_id, checkpoint_model_id = read_commandline_args()

    dataset = ALL_MODEL_DICTS[model_id]["dataset"]
    if mode == 'train':
        if model_id == 'pyramid_cifar100':
            train_pyramid_model(model_id, dataset, checkpoint_model_id=checkpoint_model_id)
        else:
            train_model(model_id, dataset, checkpoint_model_id=checkpoint_model_id)
    elif mode == 'test':
        test_model(model_id, dataset)


if __name__ == '__main__':
    main()