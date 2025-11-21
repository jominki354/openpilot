#!/usr/bin/env python3
import time
from cereal import messaging

def main():
  print("Waiting for joystick input... (Press Ctrl+C to exit)")
  sm = messaging.SubMaster(['testJoystick'])
  
  last_print = 0
  while True:
    sm.update(100)
    if sm.updated['testJoystick']:
      now = time.time()
      if now - last_print > 0.1: # Limit print rate
        axes = sm['testJoystick'].axes
        buttons = sm['testJoystick'].buttons
        print(f"Received: Axes={axes}, Buttons={buttons}")
        last_print = now
    time.sleep(0.01)

if __name__ == "__main__":
  main()
