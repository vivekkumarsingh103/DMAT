from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is alive", 200

# ⚡ Pro Tip: Add this endpoint for better uptime monitoring
@app.route('/ping')
def ping():
    return "pong", 200

def run_server():
    app.run(host='0.0.0.0', port=8080)  # Must match Render's port

threading.Thread(target=run_server).start()
