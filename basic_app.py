import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Media Service!"

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8005))
    print(f"Starting app on port {port}")
    app.run(host='0.0.0.0', port=port)

