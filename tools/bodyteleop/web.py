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

# Setup logging to file for debugging
logging.basicConfig(filename='/tmp/web_debug.log', level=logging.DEBUG, format='%(asctime)s %(message)s')
logger = logging.getLogger("bodyteleop")
logger.addHandler(logging.StreamHandler(sys.stdout)) # Also print to stdout

# Add openpilot root to path for imports to work on device
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPENPILOT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if OPENPILOT_ROOT not in sys.path:
  sys.path.insert(0, OPENPILOT_ROOT)

try:
  import pyaudio
except ImportError:
  pyaudio = None
  logger.warning("pyaudio not found, sound will be disabled")

try:
  import requests
except ImportError:
  logger.error("requests not found")
  requests = None

from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params

TELEOPDIR = f"{BASEDIR}/tools/bodyteleop"
WEBRTCD_HOST, WEBRTCD_PORT = "localhost", 5001


## UTILS
def play_sound(sound: str):
  if pyaudio is None:
    return

  SOUNDS = {
    "engage": "selfdrive/assets/sounds/engage.wav",
    "disengage": "selfdrive/assets/sounds/disengage.wav",
    "error": "selfdrive/assets/sounds/warning_immediate.wav",
  }
  if sound not in SOUNDS:
    return

  chunk = 5120
  try:
    with wave.open(os.path.join(BASEDIR, SOUNDS[sound]), "rb") as wf:
      def callback(in_data, frame_count, time_info, status):
        data = wf.readframes(frame_count)
        return data, pyaudio.paContinue

      p = pyaudio.PyAudio()
      stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                      channels=wf.getnchannels(),
                      rate=wf.getframerate(),
                      output=True,
                      frames_per_buffer=chunk,
                      stream_callback=callback)
      stream.start_stream()
      while stream.is_active():
        time.sleep(0.1)
      stream.stop_stream()
      stream.close()
      p.terminate()
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
      # Remove /static/ prefix because we set directory to TELEOPDIR/static
      # But SimpleHTTPRequestHandler serves relative to current working directory or 'directory' arg in Python 3.7+
      # Since we can't easily change the root per request, we'll handle file reading manually for safety
      # or just map the path.
      
      # Let's map /static to TELEOPDIR/static
      file_path = os.path.join(TELEOPDIR, self.path.lstrip("/"))
      if os.path.exists(file_path) and os.path.isfile(file_path):
        super().do_GET() # This might try to serve from CWD. Let's fix directory.
        return
      else:
        self.send_error(404, "File not found")
        return

    # Fallback to default behavior (will likely 404 if not in CWD)
    super().do_GET()

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
  ssl_context = create_ssl_context()

  PORT = 5002
  Handler = BodyTeleopHandler

  # Allow address reuse
  socketserver.TCPServer.allow_reuse_address = True

  logger.info(f"Attempting to bind to 0.0.0.0:{PORT}")
  with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    # Wrap the socket with SSL
    httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
    
    logger.info(f"Serving at https://0.0.0.0:{PORT}")
    try:
      httpd.serve_forever()
    except KeyboardInterrupt:
      pass
    finally:
      httpd.server_close()

if __name__ == "__main__":
  main()
