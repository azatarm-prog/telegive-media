#!/usr/bin/env python3
"""
Ultra-minimal app for Railway deployment testing
"""

import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def root():
    return jsonify({
        'status': 'running',
        'service': 'Media Management Service',
        'message': 'Minimal version is working!'
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'media-service'
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8005))
    app.run(host='0.0.0.0', port=port, debug=False)

