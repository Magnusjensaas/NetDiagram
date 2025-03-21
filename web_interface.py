#!/usr/bin/env python3
"""
Web interface module for Cisco network discovery tool.
Provides a simple web UI for viewing and interacting with network diagrams.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify

class WebInterface:
    """Creates a web interface for viewing and filtering network diagrams."""
    
    def __init__(self, output_dir: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the web interface.
        
        Args:
            output_dir: Directory where diagram files are stored
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.output_dir = output_dir
        self.app = Flask(__name__)
        self.device_data = {}
        self.setup_routes()
        
    def setup_routes(self) -> None:
        """Set up the Flask routes for the web interface."""
        
        @self.app.route('/')
        def index():
            """Main page displaying the network diagram."""
            diagrams = self._get_available_diagrams()
            device_types = self._get_device_types()
            return render_template('index.html', 
                                 diagrams=diagrams,
                                 device_types=device_types)
        
        @self.app.route('/diagrams/<path:filename>')
        def serve_diagram(filename):
            """Serve diagram files."""
            return send_from_directory(self.output_dir, filename)
        
        @self.app.route('/api/devices')
        def get_devices():
            """API endpoint to get device data."""
            return jsonify(self.device_data)
        
        @self.app.route('/api/filter', methods=['POST'])
        def filter_devices():
            """API endpoint to filter devices by type."""
            filter_types = request.json.get('types', [])
            # Logic to regenerate diagram with filters would go here
            return jsonify({'success': True, 'filter_applied': filter_types})
    
    def _get_available_diagrams(self) -> List[Dict[str, str]]:
        """
        Get list of available diagram files.
        
        Returns:
            List of dictionaries with diagram information
        """
        diagrams = []
        if os.path.exists(self.output_dir):
            for filename in os.listdir(self.output_dir):
                if filename.endswith('.html'):
                    diagrams.append({
                        'name': filename.replace('.html', ''),
                        'path': filename,
                        'type': 'interactive'
                    })
                elif filename.endswith(('.png', '.jpg', '.svg')):
                    diagrams.append({
                        'name': filename.replace(''.join(['.', filename.split('.')[-1]]), ''),
                        'path': filename,
                        'type': 'static'
                    })
        return diagrams
    
    def _get_device_types(self) -> List[str]:
        """
        Get unique device types from the data.
        
        Returns:
            List of device type strings
        """
        device_types = set()
        for device in self.device_data.values():
            device_types.add(device.get('device_type', 'unknown'))
        return list(device_types)
    
    def set_device_data(self, data: Dict[str, Dict[str, Any]]) -> None:
        """
        Set the device data for the web interface.
        
        Args:
            data: Dictionary of device data
        """
        self.device_data = data
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False) -> None:
        """
        Run the web interface.
        
        Args:
            host: Host address to bind to
            port: Port to listen on
            debug: Whether to run in debug mode
        """
        # Create templates directory and index.html if they don't exist
        templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir)
            
        # Create a basic index.html template if it doesn't exist
        index_path = os.path.join(templates_dir, 'index.html')
        if not os.path.exists(index_path):
            with open(index_path, 'w') as f:
                f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Network Topology Viewer</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { margin-bottom: 20px; }
        .controls { margin-bottom: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }
        .diagram-container { border: 1px solid #ddd; border-radius: 5px; padding: 10px; }
        .diagram-tabs { display: flex; margin-bottom: 10px; }
        .diagram-tab { padding: 8px 15px; cursor: pointer; background-color: #eee; margin-right: 5px; border-radius: 5px 5px 0 0; }
        .diagram-tab.active { background-color: #007bff; color: white; }
        .device-filter { margin-top: 10px; }
        .device-type { display: inline-block; margin-right: 10px; }
        iframe { width: 100%; height: 800px; border: none; }
        img { max-width: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Network Topology Viewer</h1>
        </div>
        
        <div class="controls">
            <h3>Display Options</h3>
            <div class="device-filter">
                <h4>Filter Device Types:</h4>
                {% for type in device_types %}
                <div class="device-type">
                    <input type="checkbox" id="type-{{ type }}" name="device-type" value="{{ type }}" checked>
                    <label for="type-{{ type }}">{{ type|title }}</label>
                </div>
                {% endfor %}
            </div>
            <button id="apply-filters" style="margin-top: 10px;">Apply Filters</button>
        </div>
        
        <div class="diagram-container">
            {% if diagrams %}
            <div class="diagram-tabs">
                {% for diagram in diagrams %}
                <div class="diagram-tab {% if loop.first %}active{% endif %}" 
                     data-path="{{ diagram.path }}" 
                     data-type="{{ diagram.type }}">
                    {{ diagram.name }}
                </div>
                {% endfor %}
            </div>
            <div id="diagram-content">
                {% set first = diagrams[0] %}
                {% if first.type == 'interactive' %}
                <iframe src="{{ url_for('serve_diagram', filename=first.path) }}"></iframe>
                {% else %}
                <img src="{{ url_for('serve_diagram', filename=first.path) }}" alt="{{ first.name }}">
                {% endif %}
            </div>
            {% else %}
            <p>No diagrams available. Please run the discovery tool first.</p>
            {% endif %}
        </div>
    </div>
    
    <script>
        // Simple tab switching
        document.querySelectorAll('.diagram-tab').forEach(tab => {
            tab.addEventListener('click', function() {
                // Set active tab
                document.querySelectorAll('.diagram-tab').forEach(t => {
                    t.classList.remove('active');
                });
                this.classList.add('active');
                
                // Update content based on diagram type
                const path = this.getAttribute('data-path');
                const type = this.getAttribute('data-type');
                const contentArea = document.getElementById('diagram-content');
                
                if (type === 'interactive') {
                    contentArea.innerHTML = `<iframe src="/diagrams/${path}"></iframe>`;
                } else {
                    contentArea.innerHTML = `<img src="/diagrams/${path}" alt="${path}">`;
                }
            });
        });
        
        // Filter functionality
        document.getElementById('apply-filters').addEventListener('click', function() {
            const selectedTypes = Array.from(
                document.querySelectorAll('input[name="device-type"]:checked')
            ).map(cb => cb.value);
            
            fetch('/api/filter', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({types: selectedTypes}),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reload the current diagram
                    const activeTab = document.querySelector('.diagram-tab.active');
                    if (activeTab) {
                        activeTab.click();
                    }
                }
            });
        });
    </script>
</body>
</html>
                """)
        
        self.logger.info(f"Starting web interface on http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)