const keyVals = { w: 0, a: 0, s: 0, d: 0 }

// EXPO curve for smoother center control (matching joystick_control.py)
const EXPO = 0.4;
function applyExpo(value) {
  return EXPO * Math.pow(value, 3) + (1 - EXPO) * value;
}

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
      // Comma 3X uses: accel=ABS_RX (Right Stick Y), steer=ABS_Z (Right Stick X)
      // L2 trigger (button 6) = brake, R2 trigger (button 7) = gas

      const deadzone = 0.03; // 3% deadzone to match joystick_control.py

      let rightStickX = gp.axes[2]; // Right stick X -> Steer
      let rightStickY = gp.axes[5]; // Right stick Y -> Accel

      // Fallback: try axis 3 if axis 5 is undefined (browser compatibility)
      if (rightStickY === undefined || rightStickY === null) {
        rightStickY = gp.axes[3];
      }

      let l2 = gp.buttons[6] ? gp.buttons[6].value : 0; // L2 trigger (brake)
      let r2 = gp.buttons[7] ? gp.buttons[7].value : 0; // R2 trigger (accel)

      // Apply deadzone
      if (Math.abs(rightStickX) < deadzone) rightStickX = 0;
      if (Math.abs(rightStickY) < deadzone) rightStickY = 0;

      // Override keyboard if gamepad is active
      if (Math.abs(rightStickX) > 0 || Math.abs(rightStickY) > 0 || l2 > 0 || r2 > 0) {
        // Calculate accel from stick + triggers
        let accel = -rightStickY; // Invert: Up (-1) becomes Gas (+1)

        // Triggers override stick (higher priority)
        if (l2 > deadzone) {
          accel = -l2; // L2 is brake (negative)
        } else if (r2 > deadzone) {
          accel = r2; // R2 is gas (positive)
        }

        // Apply EXPO curve for fine control
        x = applyExpo(accel);
        y = applyExpo(-rightStickX); // Invert: Left (-1) becomes Left steer (+1)
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
    $("#pos-vals").text(x.toFixed(3) + "," + y.toFixed(3));
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