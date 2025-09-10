from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def root():
    return jsonify({
        'service': 'Media Management Service',
        'status': 'running',
        'version': '1.0.0',
        'endpoints': [
            '/',
            '/health',
            '/api/test'
        ]
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'media-service',
        'version': '1.0.0'
    })

@app.route('/api/test')
def api_test():
    return jsonify({
        'success': True,
        'message': 'API is working',
        'timestamp': '2025-09-10T19:56:00Z'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8005))
    app.run(host='0.0.0.0', port=port, debug=False)

