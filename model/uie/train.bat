echo "Data Merged."

set model_name=uie-mini
set check_point_path=./checkpoint/model_best_mini-100
set dataset_path=../../datasets/HT-UIE/data_merge_0412

python finetune.py --device gpu --logging_steps 3000 --save_steps 3000 --eval_steps 3000 --model_name_or_path %model_name% --output_dir %check_point_path% --train_path %dataset_path%/train.txt --dev_path %dataset_path%/dev.txt --max_seq_length 512 --per_device_eval_batch_size 24 --per_device_train_batch_size 24 --num_train_epochs 100 --learning_rate 1e-5 --do_train --do_eval --do_export --export_model_dir %check_point_path% --overwrite_output_dir --disable_tqdm True --metric_for_best_model eval_f1 --load_best_model_at_end True --save_total_limit 1 --weight_decay 0.001

