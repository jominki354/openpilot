#!/usr/bin/env python3
import os
import sys
import json
import logging
import ssl
import subprocess
import threading
import time
import http.server
import socketserver
from urllib.parse import urlparse
import wave
import base64
import hashlib
import struct

import tempfile

# Setup logging to file for debugging
log_path = os.path.join(tempfile.gettempdir(), 'web_debug.log')
logging.basicConfig(filename=log_path, level=logging.DEBUG, format='%(asctime)s %(message)s')
logger = logging.getLogger("bodyteleop")
logger.addHandler(logging.StreamHandler(sys.stdout)) # Also print to stdout

# Add openpilot root to path for imports to work on device
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPENPILOT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if OPENPILOT_ROOT not in sys.path:
  sys.path.insert(0, OPENPILOT_ROOT)
  sys.path.insert(0, os.path.dirname(OPENPILOT_ROOT)) # Add parent to allow 'import openpilot'

try:
  import numpy as np
  import sounddevice as sd
except ImportError:
  np = None
  sd = None
  logger.warning("numpy or sounddevice not found, sound will be disabled")

try:
  import requests
except ImportError:
  logger.error("requests not found")
  requests = None

try:
  from openpilot.common.basedir import BASEDIR
  from openpilot.common.params import Params
except ImportError:
  try:
    import common.basedir
    import common.params
    BASEDIR = common.basedir.BASEDIR
    Params = common.params.Params
  except ImportError:
    logger.warning("Could not import BASEDIR or Params, using mocks")
    BASEDIR = tempfile.gettempdir()
    class MockParams:
      def put_bool(self, key, val):
        logger.info(f"Mock Params put_bool: {key}={val}")
      def get_bool(self, key):
        return False
    Params = MockParams
    
  # Inject into sys.modules to fix cereal imports if possible
  import sys
  import common
  sys.modules["openpilot.common"] = common

try:
  from cereal import messaging
except Exception:
  logger.warning("cereal not found, using mock messaging")
  class MockMessaging:
    def PubMaster(self, services):
      return self
    def new_message(self, service):
      class Msg:
        def __init__(self):
          self.valid = True
          self.testJoystick = self
          self.axes = []
          self.buttons = []
      return Msg()
    def send(self, service, msg):
      logger.info(f"Mock send to {service}: axes={msg.testJoystick.axes}")
  messaging = MockMessaging()

TELEOPDIR = f"{BASEDIR}/tools/bodyteleop"
WEBRTCD_HOST, WEBRTCD_PORT = "localhost", 5001


## UTILS
def play_sound(sound: str):
  if np is None or sd is None:
    return

  SOUNDS = {
    "engage": "selfdrive/assets/sounds/engage.wav",
    "disengage": "selfdrive/assets/sounds/disengage.wav",
    "error": "selfdrive/assets/sounds/warning_immediate.wav",
  }
  if sound not in SOUNDS:
    return

  try:
    with wave.open(os.path.join(BASEDIR, SOUNDS[sound]), "rb") as wf:
      fs = wf.getframerate()
      nchannels = wf.getnchannels()
      length = wf.getnframes()
      frames = wf.readframes(length)
      
      # Convert to numpy array
      audio_data = np.frombuffer(frames, dtype=np.int16)
      
      # Normalize to float32 [-1, 1]
      audio_data = audio_data.astype(np.float32) / 32768.0
      
      # Reshape for channels if needed
      if nchannels > 1:
        audio_data = audio_data.reshape(-1, nchannels)
      
      # Play
      sd.play(audio_data, fs)
      sd.wait()
      
  except Exception as e:
    logger.error(f"Error playing sound: {e}")


## SSL
def create_ssl_cert(cert_path: str, key_path: str):
  try:
    proc = subprocess.run(f'openssl req -x509 -newkey rsa:4096 -nodes -out {cert_path} -keyout {key_path} \
                          -days 365 -subj "/C=US/ST=California/O=commaai/OU=comma body"',
                          capture_output=True, shell=True)
    proc.check_returncode()
  except subprocess.CalledProcessError as ex:
    raise ValueError(f"Error creating SSL certificate:\n[stdout]\n{proc.stdout.decode()}\n[stderr]\n{proc.stderr.decode()}") from ex


def create_ssl_context():
  cert_path = os.path.join(TELEOPDIR, "cert.pem")
  key_path = os.path.join(TELEOPDIR, "key.pem")
  if not os.path.exists(cert_path) or not os.path.exists(key_path):
    logger.info("Creating certificate...")
    create_ssl_cert(cert_path, key_path)
  else:
    logger.info("Certificate exists!")
  
  # Create SSL context
  context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
  context.load_cert_chain(cert_path, key_path)
  return context


class BodyTeleopHandler(http.server.SimpleHTTPRequestHandler):
  def do_GET(self):
    if self.headers.get("Upgrade", "").lower() == "websocket":
      self.handle_websocket()
      return

    if self.path == "/":
      self.path = "/static/index.html"
    elif self.path == "/ping":
      self.send_response(200)
      self.send_header("Content-type", "text/plain")
      self.end_headers()
      self.wfile.write(b"pong")
      return
    
    # Serve static files from the correct directory
    if self.path.startswith("/static/"):
      file_path = os.path.join(TELEOPDIR, self.path.lstrip("/"))
      if os.path.exists(file_path) and os.path.isfile(file_path):
        super().do_GET()
        return
      else:
        self.send_error(404, "File not found")
        return

    # Fallback to default behavior
    super().do_GET()

  def handle_websocket(self):
    # WebSocket Handshake
    key = self.headers.get("Sec-WebSocket-Key")
    if not key:
      self.send_error(400, "Missing Sec-WebSocket-Key")
      return
    
    accept_key = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
    
    self.send_response(101)
    self.send_header("Upgrade", "websocket")
    self.send_header("Connection", "Upgrade")
    self.send_header("Sec-WebSocket-Accept", accept_key)
    self.end_headers()
    
    logger.info("WebSocket connection established")
    
    pm = messaging.PubMaster(['testJoystick'])
    
    try:
      while True:
        # Read frame
        data = self.rfile.read(2)
        if not data or len(data) < 2:
          break
          
        byte1, byte2 = struct.unpack("BB", data)
        opcode = byte1 & 0x0F
        masked = (byte2 & 0x80) >> 7
        payload_len = byte2 & 0x7F
        
        if opcode == 0x8: # Close
          logger.info("WebSocket close frame received")
          break
          
        if payload_len == 126:
          data = self.rfile.read(2)
          payload_len = struct.unpack(">H", data)[0]
        elif payload_len == 127:
          data = self.rfile.read(8)
          payload_len = struct.unpack(">Q", data)[0]
          
        masks = None
        if masked:
          masks = self.rfile.read(4)
          
        payload = self.rfile.read(payload_len)
        
        if masked:
          payload = bytearray(payload)
          for i in range(len(payload)):
            payload[i] ^= masks[i % 4]
          payload = bytes(payload)
          
        if opcode == 0x1: # Text frame
          try:
            msg = json.loads(payload.decode('utf-8'))
            if msg.get("type") == "testJoystick":
              # Format: {"type": "testJoystick", "data": {"axes": [accel, steer], "buttons": [false]}}
              data = msg.get("data", {})
              axes = data.get("axes", [0.0, 0.0])
              
              # Publish to ZMQ
              joystick_msg = messaging.new_message('testJoystick')
              joystick_msg.valid = True
              joystick_msg.testJoystick.axes = axes
              joystick_msg.testJoystick.buttons = [False] # Default buttons
              pm.send('testJoystick', joystick_msg)
            
            elif msg.get("type") == "sound":
              sound_to_play = msg.get("data")
              if sound_to_play:
                threading.Thread(target=play_sound, args=(sound_to_play,)).start()
              
          except json.JSONDecodeError:
            logger.warning("Invalid JSON received over WebSocket")
          except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            
    except Exception as e:
      logger.error(f"WebSocket connection error: {e}")
    finally:
      logger.info("WebSocket connection closed")

  def translate_path(self, path):
    # Override translate_path to serve files from TELEOPDIR
    path = path.split('?',1)[0]
    path = path.split('#',1)[0]
    # Don't allow directory traversal
    if ".." in path:
        return ""
    
    if path == "/":
        return os.path.join(TELEOPDIR, "static", "index.html")
    
    # Map URL paths to filesystem paths
    return os.path.join(TELEOPDIR, path.lstrip("/"))


  def do_POST(self):
    content_length = int(self.headers['Content-Length'])
    post_data = self.rfile.read(content_length)
    
    try:
      params = json.loads(post_data.decode('utf-8'))
    except json.JSONDecodeError:
      self.send_error(400, "Invalid JSON")
      return

    if self.path == "/offer":
      self.handle_offer(params)
    elif self.path == "/sound":
      self.handle_sound(params)
    else:
      self.send_error(404, "Not Found")

  def handle_offer(self, params):
    # Construct the body for webrtcd
    body = {
      "sdp": params["sdp"],
      "cameras": ["driver"],
      "bridge_services": ["testJoystick"],
      "extra_services": ["carState"]
    }
    
    logger.info("Sending offer to webrtcd...")
    webrtcd_url = f"http://{WEBRTCD_HOST}:{WEBRTCD_PORT}/stream"
    
    try:
      # Use requests (synchronous) instead of aiohttp
      if requests:
        response = requests.post(webrtcd_url, json=body, timeout=5)
        if response.status_code == 200:
          answer = response.json()
          self.send_response(200)
          self.send_header("Content-type", "application/json")
          self.end_headers()
          self.wfile.write(json.dumps(answer).encode('utf-8'))
        else:
          self.send_error(502, f"webrtcd returned {response.status_code}")
      else:
        self.send_error(500, "requests library not available")
    except Exception as e:
      logger.error(f"Error contacting webrtcd: {e}")
      self.send_error(502, "Failed to contact webrtcd")

  def handle_sound(self, params):
    sound_to_play = params.get("sound")
    if sound_to_play:
      # Run play_sound in a separate thread to not block the server
      threading.Thread(target=play_sound, args=(sound_to_play,)).start()
    
    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))


def main():
  logger.info("Starting web.py main...")
  # Enable joystick debug mode
  Params().put_bool("JoystickDebugMode", True)

  # Create SSL context
  ssl_context = None
  try:
    ssl_context = create_ssl_context()
  except Exception as e:
    logger.error(f"Failed to create SSL context: {e}. Falling back to HTTP.")

  PORT = 5002
  Handler = BodyTeleopHandler

  # Allow address reuse
  socketserver.TCPServer.allow_reuse_address = True

  logger.info(f"Attempting to bind to 0.0.0.0:{PORT}")
  with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    # Wrap the socket with SSL if available
    if ssl_context:
      httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
      logger.info(f"Serving at https://0.0.0.0:{PORT}")
    else:
      logger.info(f"Serving at http://0.0.0.0:{PORT}")
    
    try:
      httpd.serve_forever()
    except KeyboardInterrupt:
      pass
    finally:
      httpd.server_close()

if __name__ == "__main__":
  main()
