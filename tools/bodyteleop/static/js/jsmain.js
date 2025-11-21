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

// Display branch name
$("#branch-name").text("j-nr-s-pad");

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
      "background": "linear-gradient(90deg, #10b981, #059669)"
    });
  } else {
    $("#steer-fill").css({
      "left": (50 + y * 50) + "%",
      "width": (-y * 50) + "%",
      "background": "linear-gradient(90deg, #047857, #10b981)"
    });
  }
}, 50);

setInterval(() => {
  const dt = new Date().getTime();
  if ((dt - lastChannelMessageTime) > 1000) {
    $("#ping-time").text('-');
  }
}, 5000);

// Gamepad connection monitoring
// We use polling instead of events because Android Chrome often misses events
// until a button is pressed.

// Check for gamepads in the main loop
setInterval(() => {
  const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
  let connected = false;
  let gpId = "";
  let debugInfo = "";
  let logMsg = "Checking gamepads...\n";

  for (let i = 0; i < gamepads.length; i++) {
    const gp = gamepads[i];
    if (gp) {
      connected = true;
      gpId = gp.id;

      // Debug info: show axis values to help troubleshooting
      // Show first 6 axes
      let axesStr = "";
      for (let j = 0; j < Math.min(gp.axes.length, 8); j++) {
        axesStr += `A${j}:${gp.axes[j].toFixed(2)} `;
      }
      let buttonsStr = "";
      for (let j = 0; j < Math.min(gp.buttons.length, 8); j++) {
        buttonsStr += `B${j}:${gp.buttons[j].value.toFixed(1)} `;
      }

      debugInfo = axesStr;
      logMsg += `[GP${i}] ID: ${gp.id}\nAxes: ${axesStr}\nBtns: ${buttonsStr}\n`;
      break; // Use the first connected gamepad
    } else {
      logMsg += `[GP${i}] null\n`;
    }
  }

  if (gamepads.length === 0) {
    logMsg += "No gamepads detected by browser.\nTry pressing buttons on the controller.";
  }

  // Update Debug Console
  $("#debug-console").text(logMsg);

  const statusEl = $("#gamepad-status-main");
  if (connected) {
    if (!statusEl.hasClass("connected")) {
      statusEl.removeClass("disconnected").addClass("connected");
    }
    // Update text with ID and Debug info
    // Truncate ID if too long
    let shortId = gpId.length > 20 ? gpId.substring(0, 20) + "..." : gpId;
    statusEl.text(`${shortId} [${debugInfo}]`);
  } else {
    if (!statusEl.hasClass("disconnected")) {
      statusEl.removeClass("connected").addClass("disconnected");
      statusEl.text("Connect Your PS5 Controller");
    }
  }
}, 200); // Check every 200ms for smoother debug updates

start(pc, dc);
