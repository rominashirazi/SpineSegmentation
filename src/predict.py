"""
@Author: Sulaiman Vesal
Date: Tuesday, 04, 2020


"""

import numpy as np
import os
import matplotlib.pyplot as plt
import torch as t
from torch.utils.tensorboard import SummaryWriter
from datetime import datetime
import argparse
from utils.utils import soft_to_hard_pred, keep_largest_connected_components
from utils.loss import DiceCoefMultilabelLoss
from model.dilated_unet import Segmentation_model
from utils.metric import dice_coef_multilabel
from dataset import ImageProcessor, DataGenerator
import torch
import cv2
import pandas as pd


def predict_model(data_generator, unet_model):
    i=0
    id_n = 0
    for dataset in data_generator:
        x_batch, y_batch = dataset
        print(x_batch.shape, y_batch.shape)
        prediction = unet_model.forward(t.tensor(x_batch).cuda(), features_out=False)
        y_pred = soft_to_hard_pred(prediction.cpu().detach().numpy(), 1)

        print("The validation dice score:", dice_coef_multilabel(y_true=y_batch, y_pred=y_pred, channel='channel_first'))

        y_pred = np.moveaxis(y_pred, 1, -1)
        y_pred = np.argmax(y_pred, axis=-1)
        #y_pred = keep_largest_connected_components(mask=y_pred)

        y_batch = np.moveaxis(y_batch, 1, -1)
        y_batch = np.argmax(y_batch, axis=-1)

        plt.figure()
        plt.imshow(np.moveaxis(x_batch[id_n], source=0, destination=2), cmap='gray')
        plt.axis('off')
        plt.savefig('./results/run_raw.png',bbox_inches='tight',transparent=True)
        plt.figure()
        plt.imshow(y_batch[id_n], cmap='jet')
        plt.axis('off')
        plt.savefig('./results/run_mask.png',bbox_inches='tight',transparent=True)
        plt.figure()
        plt.imshow(y_pred[id_n], cmap='gray')
        plt.axis('off')
        #plt.show(block=True)
        plt.savefig('./results/run_pred.png',bbox_inches='tight',transparent=True)

        for im, gt in zip(y_pred, y_batch):
            plt.imsave('./results/pred_{}.png'.format(i), im)
            plt.imsave('./results/gt_{}.png'.format(i), gt)
            i+=1


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-unetlr", help="to set the learning rate for the unet", type=float, default=0.0001)
    parser.add_argument("-e", "--epochs", help="the number of epochs to train", type=int, default=300)
    parser.add_argument("-gn", "--gaussianNoise", help="whether to apply gaussian noise", action="store_true",
                        default=True)
    parser.add_argument("--n_samples", help="number of samples to train", type=int, default=100)
    parser.add_argument("-bs", "--batch_size", help="batch size of training", type=int, default=4)
    parser.add_argument("-nc", "--n_class", help="number of classes to segment", type=int, default=3)
    parser.add_argument("-nf", "--n_filter", help="number of initial filters for DR-UNET", type=int, default=32)
    parser.add_argument("-nb", "--n_block", help="number unet blocks", type=int, default=4)
    args = parser.parse_args()

    config_info = "filters {}, n_block {}".format(args.n_filter, args.n_block)
    print(config_info)

    # calculate the comments
    comments = "Verterbra_disk.unet_lr_{}_{}".format(args.unetlr, args.n_filter)
    if args.gaussianNoise:
        comments += ".gaussian_noise"
    print(comments)
    ids_valid = ImageProcessor.split_data("./input/validA.csv")
    ids_valid = pd.Series([15])
    validA_generator = DataGenerator(df=ids_valid,
                                     channel="channel_first",
                                     apply_noise=False,
                                     phase="valid",
                                     apply_online_aug=False,
                                     batch_size=5,
                                     n_samples=-1)

    unet_model = Segmentation_model(filters=args.n_filter,
                                    in_channels=3,
                                    n_block=args.n_block,
                                    bottleneck_depth=4,
                                    n_class=args.n_class)
    unet_model.load_state_dict(torch.load('./weights/{}/unet_model_checkpoint.pt'.format(comments)))

    start = datetime.now()
    t.autograd.set_detect_anomaly(True)
    predict_model(validA_generator, unet_model)
    end = datetime.now()
    print("time elapsed for testing (hh:mm:ss.ms) {}".format(end - start))

