import os
import json

path = "eval_log/aw_100b_0912"

total = 0
success = 0
for task in os.listdir(path):
    task_path = os.path.join(path, task)
    if not os.path.isdir(task_path):
        continue
    
    total += 1
    if os.path.exists(os.path.join(task_path, "score.txt")):
        with open(os.path.join(task_path, "score.txt"), "r") as f:
            score = float(f.read().strip())
            if score > 0:
                success += score
                
print(f"Total tasks: {total}, Total score: {success}, Success rate: {success/total:.2%}")
      