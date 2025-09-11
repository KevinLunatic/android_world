import os
import json
import requests
from urllib.parse import urlparse
from ipaddress import ip_address
import traceback
import time
from loguru import logger as log
import numpy as np
from PIL import Image
import base64
from io import BytesIO
import re
import shutil
from typing import Dict, List, Any
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from agent.prompts import USER_UNIFIED_PROMPT, ACTION_SPACE_UNIFIED_NO_ELEMENT_INFO, ADDITIONAL_NOTES_EVAL, ACTION_SPACE_UNIFIED
from run_suite_on_docker import AndroidEnvClient
from android_world.env import json_action

def is_ip_url(url: str) -> bool:
    try:
        ip_address(urlparse(url).hostname)
        return True
    except (ValueError, TypeError):
        return False

def call_glm_api(messages, base_url='http://172.20.92.26:5002/v1/chat/completions', top_p=0.00001, top_k=2, temperature=0.8):
    ip_url = is_ip_url(base_url)
    if not ip_url:
        api_key = "AQNtTd3LzxpCH4znWfRDiRYVQ2wbI8eAwsaBFzrq2mgMRoI9ts96jsflkeE45aXG"
        data = {
            "messages": messages,
            "model": "public-glm-4.5v-moe-think",
            "top_p": top_p,
            # "top_k": top_k,
            "temperature": temperature,
            "stream": False
        }
    else:
        data = {
            "messages": messages,
            "skip_special_tokens": False,
            "stop_token_ids": [151329, 151336],
            "include_stop_str_in_output": False,
            "n": 1,
            "num_threads": 128,
            "api_name": "tp:cogvlm-dev",
            "max_tokens": 8192,
            "top_p": top_p,
            "top_k": top_k,
            "temperature": temperature,
            "repetition_penalty": 1.1
        }

    retry = 5
    headers = {'Content-Type': 'application/json'} if ip_url else {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    while retry > 0:
        try:
            response = None
            headers = {'Content-Type': 'application/json'} if ip_url else {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
            response = requests.post(
                base_url,
                json=data,
                verify = False,
                headers = headers,
                timeout=300
            )
            if ip_url:
                return response.json()['choices'][0]['message']['content']
            else:
                response_contents = response.json()['choices'][0]['message']
                reasoning_content = response_contents.get('reasoning_content', "")
                output_content = response_contents.get('content', "")
                final_answer = f"<think>{reasoning_content}</think>{output_content}"
                return final_answer
        except Exception as e:
            log.error(f"Retry {5-retry} Error calling glm: {e}")
            if response is not None:
                if response.text:
                    try:
                        log.error(f"response.text: {json.dumps(json.loads(response.text), ensure_ascii=False)}")
                    except:
                        log.error(f"response.text: {response.text}")
                if response.status_code:
                    log.error(f"response.status_code: {response.status_code}")
            traceback.print_exc()
            time.sleep(1)
            retry -= 1
            if retry == 0:
                return None
            continue
    return None

def convert_pil_to_base64(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

class CogAgent():
    def __init__(self, env_id, task_id, client: AndroidEnvClient, eval_configs):
        self.env_id = env_id
        self.task_id = task_id
        self.seed = eval_configs['seed']
        self.inference_url = eval_configs['inference_url']
        self.save_dir = os.path.join(eval_configs['eval_result_dir'], eval_configs['exp_name'])
        
        # 健康检查
        while True:
            if not client.health():
                print(f"环境 {env_id} 不健康，等待1秒...")
                time.sleep(1)
            else:
                break
        # 重置环境
        res = client.reset(go_home=True)
        # 初始化任务套件
        # 一个任务模版只生成一个任务，所以后续 task_idx=0
        # 每个任务的 seed 可以不同
        res = client.reinitialize_suite(n_task_combinations=1, seed=self.seed)
        # 获取任务列表
        self.task_type = client.get_suite_task_list(max_index=-1)[task_id]
        self.goal = client.get_task_goal(task_type=self.task_type, task_idx=0)
        self.client = client
        try:
            self.max_steps = client.get_task_max_steps(task_type=self.task_type, task_idx=0)
        except:
            self.max_steps = eval_configs.get('max_steps', 30) # 目前已经部署的旧容器不支持获取每个任务的最大步数，默认都为30
        self.trace = []
    
    def build_msg(self, img: Image.Image):
        """构建对话消息"""
        history_steps = self.trace[:-1] # 所有历史步骤（不包含当前步骤)
        history_text_format = []
        
        step_idx = 0
        for step in history_steps:
            step_action = step.get("action", None)
            step_memory = step.get("memory", None)
            step_reason = step.get("reason", None)
            if step_action is None or step_action == "NONE":
                continue
            
            history_text_format.append(
                f"Step {step_idx}:\nMemory: {step_memory}\nReason: {step_reason}\nAction: {step_action}"
            )
            step_idx += 1
        history_text = "\n\n".join(history_text_format)
        
        prompt = USER_UNIFIED_PROMPT.format(
            task=self.goal,
            action_space=ACTION_SPACE_UNIFIED,
            history=history_text,
            additional_notes=ADDITIONAL_NOTES_EVAL
        )
        
        img_base64 = convert_pil_to_base64(img)
        
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": img_base64
                    }
                }
            ]
        }]
        
        return messages
    
    def _action_parser(self, response_text):
        # 提取出不包含 think 的 response 部分
        answer_pattern = r"<answer>(.*?)</answer>"
        answer_match = re.search(answer_pattern, response_text, re.DOTALL)
        if answer_match:
            response_text = answer_match.group(1).strip()
        elif "<think>" in response_text and "</think>" in response_text:
            response_text = response_text.split("</think>")[-1].strip()
            
        # 提取Memory
        memory_pattern = r"Memory:(.*?)Reason:"
        memory_match = re.search(memory_pattern, response_text, re.DOTALL)
        memory = memory_match.group(1).strip() if memory_match else None
        # 提取Reason
        reason_pattern = r"Reason:(.*?)Action:"
        reason_match = re.search(reason_pattern, response_text, re.DOTALL)
        reason = reason_match.group(1).strip() if reason_match else None
        # 提取Action
        pattern = r"<\|begin_of_box\|>(.*?)<\|end_of_box\|>"
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            action = match.group(1).strip()
        else:
            try:
                action = '{' + response_text.split('{')[-1].split('}')[0] + '}'
            except:
                action = None
        
        return {
            "action": action,
            "memory": memory,
            "reason": reason,
            "action_text": response_text.replace(" <|begin_of_box|> ","").replace(" <|end_of_box|> ","").replace("<|begin_of_box|>","").replace("<|end_of_box|>","")
        }

    def convert_plain_action_to_env(self, action: str | None, img_width, img_height) -> Dict | None:
        """将模型输出的动作转换为环境可执行的动作"""
        if action is None or action == "NONE":
            raise Exception("Action is None")
        try:
            action_dict = json.loads(action)
            action_type = action_dict["action_type"]
            if action_type == "status":
                return {
                    "action_type": action_type,
                    "goal_status": action_dict["goal_status"]
                }
            elif action_type == "answer":
                return {
                    "action_type": action_type,
                    "text": action_dict["text"]
                }
            elif action_type in ["click", "long_press"]:
                x1, y1, x2, y2 = action_dict["box_2d"][0]
                x_relative = (x1 + x2) / 2
                y_relative = (y1 + y2) / 2
                x_abs = int(int(x_relative) * (img_width / 1000))
                y_abs = int(int(y_relative) * (img_height / 1000))
                return {
                    "action_type": action_type,
                    "x": x_abs,
                    "y": y_abs
                }
            elif action_type == "input_text":
                x1, y1, x2, y2 = action_dict["box_2d"][0]
                x_relative = (x1 + x2) / 2
                y_relative = (y1 + y2) / 2
                x_abs = int(int(x_relative) * (img_width / 1000))
                y_abs = int(int(y_relative) * (img_height / 1000))
                return {
                    "action_type": action_type,
                    "x": x_abs,
                    "y": y_abs,
                    "text": action_dict["text"],
                    "clear_text": action_dict.get("override", True)
                }
            elif action_type in ["keyboard_enter", "navigate_home", "navigate_back", "wait"]:
                return {
                    "action_type": action_type
                }
            elif action_type == "swipe":
                if "box_2d" in action_dict and action_dict["box_2d"]:
                    x1, y1, x2, y2 = action_dict["box_2d"][0]
                    x1_abs = int(int(x1) * (img_width / 1000))
                    y1_abs = int(int(y1) * (img_height / 1000))
                    x2_abs = int(int(x2) * (img_width / 1000))
                    y2_abs = int(int(y2) * (img_height / 1000))
                    return {
                        "action_type": action_type,
                        "direction": action_dict["direction"],
                        "xmin": x1_abs,
                        "ymin": y1_abs,
                        "xmax": x2_abs,
                        "ymax": y2_abs,
                    }
                else:
                    return {
                        "action_type": action_type,
                        "direction": action_dict["direction"],
                    }
            elif action_type == "open_app":
                return {
                    "action_type": action_type,
                    "app_name": action_dict["app_name"]
                }
            elif action_type == "drag": 
                x1, y1 = action_dict["start_point"]
                x2, y2 = action_dict["end_point"]
                x1_abs = int(int(x1) * (img_width / 1000))
                y1_abs = int(int(y1) * (img_height / 1000))
                x2_abs = int(int(x2) * (img_width / 1000))
                y2_abs = int(int(y2) * (img_height / 1000))
                return {
                    "action_type": action_type,
                    "drag_start_x": x1_abs,
                    "drag_start_y": y1_abs,
                    "drag_end_x": x2_abs,
                    "drag_end_y": y2_abs
                }
            else:
                raise Exception(f"Unknown action_type: {action_type}")
        except Exception as e:
            raise Exception(f"Failed to parse action: {action}, error: {e}")
    
    def run(self):
        """执行整个任务"""
        log.info(f"[Env {self.env_id} | Task {self.task_id}] {self.task_type}, Goal: {self.goal}, Max Steps: {self.max_steps}")
        try:
            self.client.initialize_task(task_type=self.task_type, task_idx=0)
            time.sleep(2)  # 等待环境响应
            
            trace_start_time = time.time()
            for step_idx in range(self.max_steps):
                log.info(f"[Env {self.env_id} | Task {self.task_id}] Step {step_idx+1}/{self.max_steps}")
                
                screenshot_begin_time = time.time()
                _screenshot = self.client.get_screenshot().astype(np.uint8)
                log.info(f"[Env {self.env_id} | Task {self.task_id}] Screenshot time: {time.time() - screenshot_begin_time:.2f}s")
                img = Image.fromarray(_screenshot)
                img_width, img_height = img.size
                
                current_step = {}
                self.trace.append(current_step)
                msg_payload = self.build_msg(img)
                try:
                    call_start_time = time.time()
                    model_output = call_glm_api(msg_payload, base_url=self.inference_url, top_p=0.2, top_k=2, temperature=0.8)
                    log.info(f"[Env {self.env_id} | Task {self.task_id}] Call GLM time: {time.time() - call_start_time:.2f}s")
                    parsed_action = self._action_parser(model_output)
                    plain_action = parsed_action.get("action", "NONE")
                    # 如果不是合理的操作，convert_plain_action_to_env 会抛出一个错误，被except捕获
                    env_action = self.convert_plain_action_to_env(plain_action, img_width, img_height)
                    env_action_json = json_action.JSONAction(**env_action)
                except Exception as e:
                    log.error(f"Error calling glm: {e}")
                    parsed_action = {"action": "NONE", "memory": "NONE", "reason": "NONE", "action_text": "NONE"}
                    plain_action = "NONE"
                    env_action = "NONE"
                    env_action_json = None
                    
                current_step["action"] = plain_action
                current_step["memory"] = parsed_action["memory"]
                current_step["reason"] = parsed_action["reason"]
                current_step["action_text"] = parsed_action["action_text"]
                current_step['env_action'] = env_action
                
                execute_start_time = time.time()
                res = self.client.execute_action(env_action_json) if env_action_json else {"status": "skipped", "error": "No valid action"}
                log.info(f"[Env {self.env_id} | Task {self.task_id}] Execute time: {time.time() - execute_start_time:.2f}s")
                time.sleep(2)  # 等待环境响应
                
                # 保存
                os.makedirs(os.path.join(self.save_dir, f"{self.task_type}/step{step_idx}"), exist_ok=True)
                with open(os.path.join(self.save_dir, f"{self.task_type}/step{step_idx}/payload.json"), "w") as f:
                    img_step_idx = step_idx
                    for content_idx in range(len(msg_payload[0]['content'])-1,-1,-1):
                        if msg_payload[0]['content'][content_idx]['type'] == 'image_url':
                            msg_payload[0]['content'][content_idx]['image_url'] = self.save_dir+f'/{self.task_type}/step{img_step_idx}/img_step{img_step_idx}.png'
                            img_step_idx -= 1
                    output_dict = {
                        'instruction': self.goal,
                        'task_type': self.task_type,
                        'response': model_output,
                        'parsed_action': parsed_action,
                        'pyautogui_action': env_action,
                        'messages': msg_payload,
                    }
                    f.write(json.dumps(output_dict, ensure_ascii=False, indent=4))
                img.save(os.path.join(self.save_dir, f"{self.task_type}/step{step_idx}/img_step{step_idx}.png"))
                log.info(f"[Env {self.env_id} | Task {self.task_id}] Step {step_idx+1}/{self.max_steps} completed in {time.time() - screenshot_begin_time:.2f}s")
                # 检查终止条件
                if isinstance(env_action, dict) and env_action.get("action_type") == "status":
                    break
                
            # 任务结束
            task_score = self.client.get_task_score(task_type=self.task_type, task_idx=0)
            log.info(f"[Env {self.env_id} | Task {self.task_id}] Task completed, score: {task_score}")
            log.info(f"[Env {self.env_id} | Task {self.task_id}] Total time: {time.time() - trace_start_time:.2f}s")
            os.makedirs(os.path.join(self.save_dir, f"{self.task_type}"), exist_ok=True)
            with open(os.path.join(self.save_dir, f"{self.task_type}/score.txt"), 'w') as f:
                f.write(f"{task_score}")

            res = self.client.tear_down_task(task_type=self.task_type, task_idx=0)
            return self.task_type, task_score
        except Exception as e:
            log.error(f"[Env {self.env_id} | Task {self.task_id}] Error during task execution: {e}")
            traceback.print_exc()
            
            # 删除目录
            if os.path.exists(os.path.join(self.save_dir, f"{self.task_type}")):
                shutil.rmtree(os.path.join(self.save_dir, f"{self.task_type}"))
                log.info(f"[Env {self.env_id} | Task {self.task_id}] Deleted failed run directory: {os.path.join(self.save_dir, f'{self.task_type}')}")
            # 抛出异常，交由上层重新执行这个任务
            raise e