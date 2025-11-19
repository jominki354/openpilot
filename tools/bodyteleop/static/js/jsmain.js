import { handleKeyX, executePlan, getXY } from "./controls.js";
import { start, stop, lastChannelMessageTime, playSoundRequest } from "./webrtc.js";

export var pc = null;
export var dc = null;

document.addEventListener('keydown', (e) => (handleKeyX(e.key.toLowerCase(), 1)));
document.addEventListener('keyup', (e) => (handleKeyX(e.key.toLowerCase(), 0)));
$(".key-mobile").bind("mousedown touchstart", (e) => {
  e.preventDefault();
  handleKeyX($(e.target).attr('id').replace('key-', ''), 1);
});
$(".key-mobile").bind("mouseup touchend", (e) => {
  e.preventDefault();
  handleKeyX($(e.target).attr('id').replace('key-', ''), 0);
});
$(".sound").click((e) => {
  const sound = $(e.target).attr('id').replace('sound-', '')
  return playSoundRequest(sound);
});

// Display device IP
try {
  const hostname = window.location.hostname;
  if (hostname && hostname !== 'localhost' && hostname !== '127.0.0.1') {
    $("#device-ip").text(hostname);
  } else {
    $("#device-ip").text(window.location.host);
  }
} catch (e) {
  $("#device-ip").text("-");
}

// Update input visualization
setInterval(() => {
  const { x, y } = getXY();

  // Update accel meter
  $("#accel-value").text(x.toFixed(3));
  if (x >= 0) {
    $("#accel-fill").css({
      "left": "50%",
      "width": (x * 50) + "%",
      "background": "linear-gradient(90deg, #10b981, #059669)"
    });
  } else {
    $("#accel-fill").css({
      "left": (50 + x * 50) + "%",
      "width": (-x * 50) + "%",
      "background": "linear-gradient(90deg, #dc2626, #ef4444)"
    });
  }

  // Update steer meter
  $("#steer-value").text(y.toFixed(3));
  if (y >= 0) {
    $("#steer-fill").css({
      "left": "50%",
      "width": (y * 50) + "%",
      "background": "linear-gradient(90deg, #6366f1, #8b5cf6)"
    });
  } else {
    $("#steer-fill").css({
      "left": (50 + y * 50) + "%",
      "width": (-y * 50) + "%",
      "background": "linear-gradient(90deg, #8b5cf6, #6366f1)"
    });
  }
}, 50);

setInterval(() => {
  const dt = new Date().getTime();
  if ((dt - lastChannelMessageTime) > 1000) {
    $("#battery").text("-");
    $("#ping-time").text('-');
  }
}, 5000);

// Gamepad connection monitoring
window.addEventListener("gamepadconnected", (e) => {
  console.log("Gamepad connected:", e.gamepad.id);
  $("#gamepad-status-main").text(e.gamepad.id).removeClass("disconnected").addClass("connected");
});

window.addEventListener("gamepaddisconnected", (e) => {
  console.log("Gamepad disconnected");
  $("#gamepad-status-main").text("Connect Your PS5 Controller").removeClass("connected").addClass("disconnected");
});

// Check for already connected gamepads on page load
const checkGamepads = () => {
  const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
  for (let i = 0; i < gamepads.length; i++) {
    if (gamepads[i]) {
      $("#gamepad-status-main").text(gamepads[i].id).removeClass("disconnected").addClass("connected");
      return;
    }
  }
};
checkGamepads();

start(pc, dc);
