import time
from android_world.env import json_action
import numpy as np
from run_suite_on_docker import AndroidEnvClient
import matplotlib.pyplot as plt
from PIL import Image

# client = AndroidEnvClient()

# while True:
#   if not client.health():
#     print("Environment is not healthy, waiting for 1 second...")
#     time.sleep(1)
#   else:
#     break

# res = client.reset(go_home=True)
# print(f"reset response: {res}")

# screenshot = client.get_screenshot()
# print("Screen dimensions:", screenshot.shape, screenshot.dtype)
# screenshot = screenshot.astype(np.uint8)
# img = Image.fromarray(screenshot)
# img.save("screenshot_0.png")

# res = client.execute_action(
#     json_action.JSONAction(action_type="open_app", app_name="Contacts")
# )
# print(f"execute_action response: {res}")
# time.sleep(3)  # Wait for the app to open

# screenshot = client.get_screenshot()
# print("Screen dimensions:", screenshot.shape, screenshot.dtype)
# screenshot = screenshot.astype(np.uint8)
# img = Image.fromarray(screenshot)
# img.save("screenshot_1.png")

# res = client.execute_action(
#     json_action.JSONAction(action_type="open_app", app_name="Chrome")
# )
# print(f"execute_action response: {res}")
# time.sleep(3)  # Wait for the app to open

# screenshot = client.get_screenshot()
# print("Screen dimensions:", screenshot.shape, screenshot.dtype)
# screenshot = screenshot.astype(np.uint8)
# img = Image.fromarray(screenshot)
# img.save("screenshot_2.png")

# res = client.execute_action(
#     json_action.JSONAction(action_type="open_app", app_name="Broccoli")
# )
# print(f"execute_action response: {res}")
# time.sleep(3)  # Wait for the app to open

# screenshot = client.get_screenshot()
# print("Screen dimensions:", screenshot.shape, screenshot.dtype)
# screenshot = screenshot.astype(np.uint8)
# img = Image.fromarray(screenshot)
# img.save("screenshot_3.png")

if __name__ == "__main__":
    pass