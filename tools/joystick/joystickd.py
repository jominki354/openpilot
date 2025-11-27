#!/usr/bin/env python3
import os
import sys

# Add openpilot root to path for imports to work on device
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPENPILOT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if OPENPILOT_ROOT not in sys.path:
  sys.path.insert(0, OPENPILOT_ROOT)

import math

from cereal import messaging, car
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL, Ratekeeper
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog

LongCtrlState = car.CarControl.Actuators.LongControlState
MAX_LAT_ACCEL = 3.75


def validate_joystick_input(value: float, axis_name: str) -> float:
  """Validate and clamp joystick input values.

  Args:
    value: Raw joystick input value
    axis_name: Name of axis for logging

  Returns:
    Validated and clamped value in range [-1.0, 1.0]
  """
  # Check for NaN or Infinity
  if not math.isfinite(value):
    cloudlog.warning(f"Invalid {axis_name} value (NaN/Inf), resetting to 0")
    return 0.0

  # Clamp to valid range
  clamped = max(-1.0, min(1.0, value))
  if clamped != value:
    cloudlog.debug(f"{axis_name} value {value} clamped to {clamped}")

  return clamped


def joystickd_thread():
  import time

  params = Params()
  cloudlog.info("joystickd is waiting for CarParams")

  # Wait for CarParams with timeout
  timeout = 30  # 30 seconds
  start_time = time.time()
  CP = None
  while time.time() - start_time < timeout:
    cp_bytes = params.get("CarParams")
    if cp_bytes:
      CP = messaging.log_from_bytes(cp_bytes, car.CarParams)
      cloudlog.info("joystickd: CarParams loaded successfully")
      break
    time.sleep(0.5)

  if CP is None:
    cloudlog.warning("joystickd: CarParams not available after 30s, using default vehicle model")
    CP = car.CarParams.new_message()

  VM = VehicleModel(CP)

  # Default values are now set in manager.py get_default_params()
  # Previous values for smoothing
  prev_steer = 0.0
  prev_accel = 0.0

  # Cache parameters (update every 1 second instead of every loop)
  smoothing_enabled = params.get_bool("JoystickSmoothingEnabled")
  steer_sensitivity = 1.0
  steer_gain = 1.0
  accel_sensitivity = 1.0
  accel_gain = 1.0
  deadzone = 0.0
  param_update_counter = 0

  sm = messaging.SubMaster(['carState', 'onroadEvents', 'liveParameters', 'selfdriveState', 'testJoystick'], frequency=1.0 / DT_CTRL)
  pm = messaging.PubMaster(['carControl', 'controlsState'])

  # Connection state tracking
  joystick_connected = False
  last_joystick_time = 0.0
  connection_lost_logged = False

  rk = Ratekeeper(100, print_delay_threshold=None)
  while 1:
    try:
      sm.update(0)

      # Update parameters only once per second (100Hz -> 1Hz)
      if param_update_counter % 100 == 0:
        smoothing_enabled = params.get_bool("JoystickSmoothingEnabled")
        if smoothing_enabled:

          def get_param_int(key, default):
            value = params.get(key)
            if value is None or value == b'':
              return default
            try:
              return int(value)
            except (ValueError, TypeError):
              return default

          steer_sensitivity = get_param_int("JoystickSteeringSensitivity", 100) / 100.0
          steer_gain = get_param_int("JoystickSteeringGain", 100) / 100.0
          accel_sensitivity = get_param_int("JoystickAccelSensitivity", 100) / 100.0
          accel_gain = get_param_int("JoystickAccelGain", 100) / 100.0
          deadzone = get_param_int("JoystickDeadzone", 0) / 100.0

      param_update_counter += 1

      cc_msg = messaging.new_message('carControl')
      cc_msg.valid = True
      CC = cc_msg.carControl

      # Respect car state instead of forcing enabled
      # Only enable if selfdriveState allows and car is in valid state
      CS = sm['carState']
      selfdrive_enabled = sm['selfdriveState'].enabled

      # Enable controls in joystick mode, respecting safety constraints
      CC.enabled = selfdrive_enabled or params.get_bool("JoystickDebugMode")
      CC.latActive = CC.enabled and not CS.steerFaultPermanent and not CS.steerFaultTemporary
      CC.longActive = CC.enabled and CP.openpilotLongitudinalControl

      CC.cruiseControl.cancel = sm['carState'].cruiseState.enabled and (not CC.enabled or not CP.pcmCruise)
      CC.hudControl.leadDistanceBars = 2
      CC.hudControl.leadVisible = True

      actuators = CC.actuators

      # reset joystick if it hasn't been received in a while
      should_reset_joystick = sm.recv_frame['testJoystick'] == 0 or (sm.frame - sm.recv_frame['testJoystick']) * DT_CTRL > 0.2

      # Track connection state
      current_time = time.time()
      if not should_reset_joystick:
        if not joystick_connected:
          cloudlog.info("Joystick connected")
          joystick_connected = True
          connection_lost_logged = False
        last_joystick_time = current_time
        joystick_axes = sm['testJoystick'].axes
      else:
        if joystick_connected and not connection_lost_logged:
          cloudlog.warning(f"Joystick connection lost (last received {current_time - last_joystick_time:.1f}s ago)")
          joystick_connected = False
          connection_lost_logged = True
        joystick_axes = [0.0, 0.0]

      # Get raw joystick inputs with validation
      try:
        accel_input = validate_joystick_input(joystick_axes[0], "accel") if len(joystick_axes) > 0 else 0.0
        steer_input = validate_joystick_input(joystick_axes[1], "steer") if len(joystick_axes) > 1 else 0.0
      except Exception as e:
        cloudlog.error(f"Error reading joystick axes: {e}")
        accel_input = 0.0
        steer_input = 0.0

      # Apply settings if enabled (use cached values)
      if smoothing_enabled:
        # Apply deadzone (0 = disabled)
        if deadzone > 0:
          if abs(steer_input) < deadzone:
            steer_input = 0.0
          if abs(accel_input) < deadzone:
            accel_input = 0.0

        # Apply smoothing (100 = instant/disabled, <100 = smooth)
        if steer_sensitivity < 1.0:
          steer_output = prev_steer * (1.0 - steer_sensitivity) + steer_input * steer_sensitivity
          prev_steer = steer_output
        else:
          steer_output = steer_input

        if accel_sensitivity < 1.0:
          accel_output = prev_accel * (1.0 - accel_sensitivity) + accel_input * accel_sensitivity
          prev_accel = accel_output
        else:
          accel_output = accel_input

        # Apply gain (100 = 1:1/disabled, !=100 = scaled)
        if steer_gain != 1.0:
          steer_output = steer_output * steer_gain
          steer_output = max(-1.0, min(1.0, steer_output))

        if accel_gain != 1.0:
          accel_output = accel_output * accel_gain
          accel_output = max(-1.0, min(1.0, accel_output))
      else:
        # Smoothing disabled: direct input
        steer_output = steer_input
        accel_output = accel_input

      if CC.longActive:
        # Apply Max Speed Limit
        max_speed = params.get_int("JoystickMaxSpeed")
        current_speed_kph = sm['carState'].vEgo * 3.6

        if max_speed > 0 and current_speed_kph > max_speed and accel_output > 0:
          accel_output = 0.0

        actuators.accel = 6.0 * max(-1.0, min(1.0, accel_output))
        # Always use pid mode in joystick mode to allow starting from stop
        actuators.longControlState = LongCtrlState.pid

        # Auto-resume if accelerating but cruise is disabled (for standstill start)
        if accel_output > 0 and not sm['carState'].cruiseState.enabled:
          cc_msg.carControl.cruiseControl.resume = True

      if CC.latActive:
        max_curvature = MAX_LAT_ACCEL / max(sm['carState'].vEgo ** 2, 5)
        max_angle = math.degrees(VM.get_steer_from_curvature(max_curvature, sm['carState'].vEgo, sm['liveParameters'].roll))

        actuators.torque = max(-1.0, min(1.0, steer_output))
        actuators.steeringAngleDeg, actuators.curvature = actuators.torque * max_angle, actuators.torque * -max_curvature

      pm.send('carControl', cc_msg)

      cs_msg = messaging.new_message('controlsState')
      cs_msg.valid = True
      controlsState = cs_msg.controlsState
      controlsState.lateralControlState.init('debugState')

      lp = sm['liveParameters']
      steer_angle_without_offset = math.radians(sm['carState'].steeringAngleDeg - lp.angleOffsetDeg)
      controlsState.curvature = -VM.calc_curvature(steer_angle_without_offset, sm['carState'].vEgo, lp.roll)

      pm.send('controlsState', cs_msg)

      rk.keep_time()
    except Exception as e:
      cloudlog.exception(f"Error in joystickd main loop: {e}")
      # Continue running but reset to safe state
      time.sleep(0.1)


def main():
  joystickd_thread()


if __name__ == "__main__":
  main()
