import { handleKeyX, executePlan } from "./controls.js";
import { start, stop, lastChannelMessageTime, playSoundRequest } from "./webrtc.js";

export var pc = null;
export var dc = null;

document.addEventListener('keydown', (e) => (handleKeyX(e.key.toLowerCase(), 1)));
document.addEventListener('keyup', (e) => (handleKeyX(e.key.toLowerCase(), 0)));
$(".keys").bind("mousedown touchstart", (e) => handleKeyX($(e.target).attr('id').replace('key-', ''), 1));
$(".keys").bind("mouseup touchend", (e) => handleKeyX($(e.target).attr('id').replace('key-', ''), 0));
$("#plan-button").click(executePlan);
$(".sound").click((e) => {
  const sound = $(e.target).attr('id').replace('sound-', '')
  return playSoundRequest(sound);
});

setInterval(() => {
  const dt = new Date().getTime();
  if ((dt - lastChannelMessageTime) > 1000) {
    $(".pre-blob").removeClass('blob');
    $("#battery").text("-");
    $("#ping-time").text('-');
    $("video")[0].load();
  }
}, 5000);

// Gamepad connection monitoring
window.addEventListener("gamepadconnected", (e) => {
  console.log("Gamepad connected:", e.gamepad.id);
  $("#gamepad-status").text("Gamepad: " + e.gamepad.id).css("color", "#33ab4c");
});

window.addEventListener("gamepaddisconnected", (e) => {
  console.log("Gamepad disconnected");
  $("#gamepad-status").text("Gamepad: Not Connected").css("color", "#888");
});

// Check for already connected gamepads on page load
const checkGamepads = () => {
  const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
  for (let i = 0; i < gamepads.length; i++) {
    if (gamepads[i]) {
      $("#gamepad-status").text("Gamepad: " + gamepads[i].id).css("color", "#33ab4c");
      return;
    }
  }
};
checkGamepads();

start(pc, dc);
