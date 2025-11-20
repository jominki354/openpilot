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

  // Gamepad input
  const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
  for (let i = 0; i < gamepads.length; i++) {
    const gp = gamepads[i];
    if (gp) {
      const deadzone = 0.05; // Increased deadzone slightly

      // Debug: Log axes to help user find correct mapping
      // This will be displayed in the UI if we add a debug element

      // Try to detect which stick is being used (Left or Right)
      // Standard: Left(0,1), Right(2,3)
      // Android/Some controllers might be different

      let axis0 = gp.axes[0] || 0; // Left Stick X
      let axis1 = gp.axes[1] || 0; // Left Stick Y
      let axis2 = gp.axes[2] || 0; // Right Stick X
      let axis3 = gp.axes[3] || 0; // Right Stick Y (Standard)
      let axis5 = gp.axes[5] || 0; // Right Stick Y (Some controllers)

      let steer = 0;
      let accel = 0;

      // Check Right Stick first (Preferred)
      if (Math.abs(axis2) > deadzone || Math.abs(axis3) > deadzone || Math.abs(axis5) > deadzone) {
        steer = axis2;
        // Use axis 3 or 5, whichever has input
        accel = (Math.abs(axis3) > Math.abs(axis5)) ? -axis3 : -axis5;
      }
      // Fallback to Left Stick if Right Stick is idle
      else if (Math.abs(axis0) > deadzone || Math.abs(axis1) > deadzone) {
        steer = axis0;
        accel = -axis1;
      }

      // Triggers for Accel/Brake (L2/R2)
      let l2 = 0;
      let r2 = 0;

      // Button objects (Standard)
      if (gp.buttons[6]) l2 = gp.buttons[6].value;
      if (gp.buttons[7]) r2 = gp.buttons[7].value;

      // Apply deadzone to triggers
      if (l2 < deadzone) l2 = 0;
      if (r2 < deadzone) r2 = 0;

      // Override stick accel if triggers are used
      if (l2 > 0 || r2 > 0) {
        if (l2 > 0) accel = -l2; // Brake
        if (r2 > 0) accel = r2;  // Gas
      }

      // Apply EXPO and update x, y if there is any input
      if (Math.abs(steer) > deadzone || Math.abs(accel) > deadzone || l2 > 0 || r2 > 0) {
        x = applyExpo(accel);
        y = applyExpo(-steer); // Invert steer for correct direction
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