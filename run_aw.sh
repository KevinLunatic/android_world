nohup python -u run_aw.py \
    --num_worlds 2 \
    --num_tasks 2 \
    --max_steps 5 \
    --seed 42 \
    --inference_url https://api.chatglm.cn/v1/chat/completions \
    --eval_result_dir /home/ubuntu/liwenkai/android_world/eval_log \
    --exp_name aw_max_step_30_0911 > run_log/aw_max_step_30_0911.log 2>&1 &