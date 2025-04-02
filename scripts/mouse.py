import pyautogui
import time

w, h = pyautogui.size()

while True:
    pyautogui.moveTo(100,100, duration=1)
    pyautogui.moveTo(200,100, duration=1)
    pyautogui.moveTo(200,200, duration=1)
    pyautogui.moveTo(100,200, duration=1)

