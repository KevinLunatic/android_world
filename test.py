from loguru import logger as log
from run_suite_on_docker import AndroidEnvClient

client = AndroidEnvClient(url="http://localhost:5000")

res = client.reset(go_home=True)
print(f"reset response: {res}")

task_list = client.get_suite_task_list(max_index=-1)
print(task_list)

for task_type in task_list:
    res = client.get_task_max_steps(task_type=task_type, task_idx=0)
    print(f"max_steps response: {res}")