import torch
import pytorch_lightning as pl
import numpy as np
import pandas as pd
import os
import argparse
from model import Epitope_Clsfr
from utils import get_dataset
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, multilabel_confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
from tqdm import tqdm

# Usage
'''
python test.py
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--batch_size", default=32, type=int)
    parser.add_argument("-lr", "--learning_rate", default=2e-5, type=float)
    parser.add_argument("-c", "--classes", default=7, type=int)
    parser.add_argument("-lm", "--language_model", default='mBLM', type=str)
    parser.add_argument("-l", "--layers", default=1, type=int)
    parser.add_argument("-hd", "--hidden_dim", default=768, type=int)
    parser.add_argument("-dp", "--dataset_path", default='result/', type=str)
    parser.add_argument("-ckp", "--checkpoint_path", default='checkpoint/', type=str) 
    parser.add_argument("-ckn","--checkpoint_name", default='mBLM.ckpt', type=str)
    parser.add_argument("-n", "--name", default='mBLM_attention', type=str)
    parser.add_argument("-o", "--output_path", default='result/', type=str)
    args = parser.parse_args()


    # dataloader
    if  args.language_model == 'onehot':
        train_loader, val_loader, test_loader = get_dataset(args.dataset_path, batch_size=args.batch_size,LM=False)
    elif  args.language_model == 'mBLM':
        train_loader, val_loader, test_loader = get_dataset(args.dataset_path, batch_size=args.batch_size,LM='mBLM')
    elif  args.language_model == 'esm2_t33_650M_UR50D':
        train_loader, val_loader, test_loader = get_dataset(args.dataset_path, batch_size=args.batch_size,LM='esm2_t33_650M')
    else:
        train_loader, val_loader, test_loader = get_dataset(args.dataset_path, batch_size=args.batch_size)
    trainer = pl.Trainer()
    # Check whether pretrained model exists. If yes, load it and skip training
    pretrained_filename = os.path.join(args.checkpoint_path+args.name+'/', args.checkpoint_name)
    if os.path.isfile(pretrained_filename):
        print("Found pretrained model, loading...")
        model = Epitope_Clsfr.load_from_checkpoint(pretrained_filename,classes=args.classes,hidden_dim=args.hidden_dim,layers=args.layers,class_weights=None,lm_model_name = args.language_model)
        model.eval()
        # test on test set 
        test_result = trainer.test(model,test_loader)
        # test on val set 
        val_result = trainer.test(model,val_loader)

    # export prediction table and confusion matrix
        # create empty lists to store the true and predicted labels
        true_labels_ls = []
        predicted_labels_ls = []
        predicted_probabilities = []

        classes = ["HA:Head", "HA:Stem","HIV", "S:NTD", "S:RBD", "S:S2", "Others"]
        # loop over the test data and predict the labels
        with torch.no_grad():
            for batch in tqdm(test_loader,desc="mBLM on test set", leave=False):
                # get the inputs and labels
                inputs, labels,_ = batch
                outputs = model(inputs)
                # get model prediction probabilities
                probs = torch.softmax(outputs,dim=1)
                # get model predicted classes index
                predicted = torch.argmax(outputs, dim=1)

                predicted_probabilities.append(probs)
                true_labels_ls.append(labels)
                predicted_labels_ls.append(predicted)

        labels_all = np.concatenate(true_labels_ls)
        predicted_all = np.concatenate(predicted_labels_ls)
        probabilities_all = np.concatenate(predicted_probabilities)
        # read df
        df = pd.read_csv(f'{args.output_path}epitope_test.tsv',sep='\t')
        df['predicted_class'] = predicted_all
        df['real_label'] = labels_all
        df['predicted_probability'] = probabilities_all[np.arange(len(predicted_all)), predicted_all]
        df.to_csv(f'{args.output_path}{args.name}_epitope_test_prediction.tsv',sep='\t')

        # create the confusion matrix
        cm = confusion_matrix(labels_all, predicted_all)
        # plot the confusion matrix
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        # classes = [str(i) for i in range(cm.shape[0])]
        # plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
        sns.heatmap(cm, annot=True, cmap='Blues', xticklabels=classes, yticklabels=classes, fmt='.2f')
        plt.title("Normalized confusion matrix")
        plt.ylabel('True label')
        plt.xlabel('Predicted label')
        plt.savefig(f'{args.output_path}{args.name}_confusion_matrix.png', dpi=300)





