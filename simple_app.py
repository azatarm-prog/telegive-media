#!/usr/bin/env python3
"""
Simplified Media Management Service for Railway deployment debugging
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS

def create_simple_app():
    """Create a minimal Flask application for testing"""
    
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SERVICE_NAME'] = os.getenv('SERVICE_NAME', 'media-service')
    
    # Enable CORS
    CORS(app, origins="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Simple health check"""
        return jsonify({
            'status': 'healthy',
            'service': app.config.get('SERVICE_NAME', 'media-service'),
            'version': '1.0.0',
            'message': 'Service is running'
        }), 200
    
    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint"""
        return jsonify({
            'service': 'Media Management Service',
            'status': 'running',
            'endpoints': [
                '/health',
                '/api/test'
            ]
        }), 200
    
    @app.route('/api/test', methods=['GET'])
    def api_test():
        """Test API endpoint"""
        return jsonify({
            'success': True,
            'message': 'API is working',
            'method': request.method
        }), 200
    
    return app

# Create application instance
app = create_simple_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8005))
    app.run(host='0.0.0.0', port=port, debug=False)

