###!/usr/bin/env bash

# for single card eval
# python eval.py -c ../configs/PPLCNetV2_base.yaml -o Global.pretrained_model=../../app/inference_model/ch_cls

# for multi-cards eval
#python -m paddle.distributed.launch --gpus="0,1,2,3" tools/eval.py -c ./ppcls/configs/ImageNet/ResNet/ResNet50.yaml
python -m paddle.distributed.launch  eval.py -c ../configs/PPLCNetV2_base.yaml -o Global.pretrained_model=../../app/inference_model/ch_cls