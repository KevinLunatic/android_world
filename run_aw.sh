nohup python -u run_aw.py \
    --num_worlds 50 \
    --num_tasks 116 \
    --max_steps 30 \
    --seed 42 \
    --inference_url https://api.chatglm.cn/v1/chat/completions \
    --eval_result_dir /home/ubuntu/liwenkai/android_world/eval_log \
    --exp_name aw_100b_0912 > run_log/aw_100b_0912.log 2>&1 &