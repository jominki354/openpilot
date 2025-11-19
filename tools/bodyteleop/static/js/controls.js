const keyVals = { w: 0, a: 0, s: 0, d: 0 }

export function getXY() {
  // Keyboard input
  let x = -keyVals.w + keyVals.s
  let y = -keyVals.d + keyVals.a

  // Gamepad input (PS5 DualSense)
  const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
  for (let i = 0; i < gamepads.length; i++) {
    const gp = gamepads[i];
    if (gp) {
      // PS5 Controller Mapping (Standard Gamepad API)
      // Axis 0: Left Stick X (Left/Right) -> Steering
      // Axis 1: Left Stick Y (Up/Down) -> Accel/Brake

      // Deadzone
      const deadzone = 0.05;

      let axis0 = gp.axes[0]; // Left/Right
      let axis1 = gp.axes[1]; // Up/Down

      if (Math.abs(axis0) < deadzone) axis0 = 0;
      if (Math.abs(axis1) < deadzone) axis1 = 0;

      // Mix gamepad input if active (override keyboard)
      if (Math.abs(axis0) > 0 || Math.abs(axis1) > 0) {
        // joystickd expects:
        // axes[0] = Accel (-1 to 1)
        // axes[1] = Steer (-1 to 1)

        // Browser gamepad: Up is -1, Down is +1, Left is -1, Right is +1
        // We want: Gas is +1, Brake is -1, Left steer is +1, Right steer is -1
        x = -axis1; // Invert Y axis: Up (-1) becomes Gas (+1)
        y = -axis0; // Invert X axis: Left (-1) becomes Left steer (+1)
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