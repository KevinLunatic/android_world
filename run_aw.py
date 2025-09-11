import time
from android_world.env import json_action
import numpy as np
from run_suite_on_docker import AndroidEnvClient
import matplotlib.pyplot as plt
from PIL import Image
import multiprocessing
from multiprocessing import Process, Queue
import queue
from tqdm import tqdm
import os
import traceback
from agent.agent import CogAgent
import argparse
from loguru import logger as log
import tabulate

def env_run(env_id, task_queue: Queue, result_queue: Queue, eval_configs):
    """每个环境的独立工作进程"""
    # 初始化客户端
    url = f"http://localhost:{5000+env_id}"
    client = AndroidEnvClient(url)
    while True:
        # 从队列获取任务，超时后检查是否还有任务
        try:
            task_id = task_queue.get(timeout=2)
        except queue.Empty:
            # 队列空，正常退出
            break
        except Exception as e:
            log.error(f"Env {env_id} get task error: {e}")
            break
            
        # 执行任务，若失败会把任务id放回队列
        try:
            agent = CogAgent(env_id, task_id, client, eval_configs)
            task_type, result = agent.run()
            result_queue.put((env_id, task_type, result))
        except Exception as e:
            log.error(f"[Env {env_id} | Task {task_id}] Error: {e}")
            log.error(f"Put task {task_id} back to queue.")
            task_queue.put(task_id)
            continue
        
def _main(eval_configs):
    num_envs = eval_configs['num_worlds']
    num_tasks = eval_configs['num_tasks']
    
    # 创建任务队列和结果队列
    task_queue = Queue()
    result_queue = Queue()
    
    # 将所有任务放入队列
    for task_id in range(num_tasks):
        task_queue.put(task_id)

    log.info(f"Run {num_tasks} tasks with {num_envs} environments")

    # 为每个环境创建独立的工作进程
    processes = []
    for env_id in range(num_envs):
        p = Process(target=env_run, args=(env_id, task_queue, result_queue, eval_configs))
        p.start()
        processes.append(p)
    
    # 等待所有进程完成
    for p in processes:
        p.join()
        
    # 收集结果
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())
    print(tabulate.tabulate(results, headers=["Env ID", "Task ID", "Score"]))
    
    # 计算结果
    avg_score = np.mean([res[2] for res in results if res[2] is not None]) * 100
    
    log.info(f"All tasks completed.")
    log.info(f"Total completed tasks: {len(results)}, average score: {avg_score:.2f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--num_worlds', type=int, default=30)
    parser.add_argument('--num_tasks', type=int, default=116)
    parser.add_argument('--max_steps', type=int, default=30)
    parser.add_argument('--seed', type=int, default=42) # -1 代表随机seed
    parser.add_argument('--inference_url', type=str, default='https://api.chatglm.cn/v1/chat/completions')
    parser.add_argument('--eval_result_dir', type=str, default='/home/ubuntu/liwenkai/android_world/eval_log')
    parser.add_argument('--exp_name', type=str, default='test_100b_0911')
    
    args = parser.parse_args()
    
    eval_configs = {
        'num_worlds': args.num_worlds,
        'num_tasks': args.num_tasks,
        'max_steps': args.max_steps,
        'seed': args.seed,
        'inference_url': args.inference_url,
        'eval_result_dir': args.eval_result_dir,
        'exp_name': args.exp_name,
    }

    _main(eval_configs)
