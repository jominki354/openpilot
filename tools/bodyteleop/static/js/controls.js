const keyVals = { w: 0, a: 0, s: 0, d: 0 }

export function getXY() {
  // Keyboard input
  let x = -keyVals.w + keyVals.s
  let y = -keyVals.d + keyVals.a

  // Gamepad input (PS5 DualSense - matching joystick_control.py)
  const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
  for (let i = 0; i < gamepads.length; i++) {
    const gp = gamepads[i];
    if (gp) {
      // PS5 Controller Mapping (Standard Gamepad API)
      // IMPORTANT: joystick_control.py uses:
      // - Comma 3X: accel=ABS_RX (Right Stick Y), steer=ABS_Z (Right Stick X)
      // - flip_map: ABS_RY (L2 trigger) flips accel to negative (brake)
      //
      // Browser Gamepad API:
      // - Axis 2: Right Stick X (Left/Right) -> Steering
      // - Axis 5: Right Stick Y (Up/Down) -> Accel (Chrome/Firefox may differ)
      // - buttons[6].value: L2 trigger (0~1) -> Brake
      // - buttons[7].value: R2 trigger (0~1) -> Accel boost

      // Deadzone
      const deadzone = 0.05;

      let rightStickX = gp.axes[2]; // Right stick X -> Steer
      let rightStickY = gp.axes[5]; // Right stick Y -> Accel (may be axis 3 or 5)

      // Fallback: try axis 3 if axis 5 is undefined
      if (rightStickY === undefined || rightStickY === null) {
        rightStickY = gp.axes[3];
      }

      let l2 = gp.buttons[6] ? gp.buttons[6].value : 0; // L2 trigger (brake)
      let r2 = gp.buttons[7] ? gp.buttons[7].value : 0; // R2 trigger (accel)

      if (Math.abs(rightStickX) < deadzone) rightStickX = 0;
      if (Math.abs(rightStickY) < deadzone) rightStickY = 0;

      // Mix gamepad input if active (override keyboard)
      if (Math.abs(rightStickX) > 0 || Math.abs(rightStickY) > 0 || l2 > 0 || r2 > 0) {
        // joystickd expects:
        // axes[0] = Accel (-1 to 1): negative = brake, positive = gas
        // axes[1] = Steer (-1 to 1)

        // Calculate accel from stick + triggers
        let accel = -rightStickY; // Invert: Up (-1) becomes Gas (+1)

        // L2 = brake (negative accel), R2 = gas (positive accel)
        // Triggers override stick
        if (l2 > deadzone) {
          accel = -l2; // L2 is brake (negative)
        } else if (r2 > deadzone) {
          accel = r2; // R2 is gas (positive)
        }

        x = accel;
        y = -rightStickX; // Invert: Left (-1) becomes Left steer (+1)
      }
    }
  }

  return { x, y }
}

export const handleKeyX = (key, setValue) => {
  if (['w', 'a', 's', 'd'].includes(key)) {
    keyVals[key] = setValue;
    let color = "#333";
    if (setValue === 1) {
      color = "#e74c3c";
    }
    $("#key-" + key).css('background', color);
    const { x, y } = getXY();
    $("#pos-vals").text(x + "," + y);
  }
};

export async function executePlan() {
  let plan = $("#plan-text").val();
  const planList = [];
  plan.split("\n").forEach(function (e) {
    let line = e.split(",").map(k => parseInt(k));
    if (line.length != 5 || line.slice(0, 4).map(e => [1, 0].includes(e)).includes(false) || line[4] < 0 || line[4] > 10) {
      console.log("invalid plan");
    }
    else {
      planList.push(line)
    }
  });

  async function execute() {
    for (var i = 0; i < planList.length; i++) {
      let [w, a, s, d, t] = planList[i];
      while (t > 0) {
        console.log(w, a, s, d, t);
        if (w == 1) { $("#key-w").mousedown(); }
        if (a == 1) { $("#key-a").mousedown(); }
        if (s == 1) { $("#key-s").mousedown(); }
        if (d == 1) { $("#key-d").mousedown(); }
        await sleep(50);
        $("#key-w").mouseup();
        $("#key-a").mouseup();
        $("#key-s").mouseup();
        $("#key-d").mouseup();
        t = t - 0.05;
      }
    }
  }
  execute();
}