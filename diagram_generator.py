#!/usr/bin/env python3
"""
Diagram generator module for Cisco network discovery tool.
Creates visual network diagrams based on collected data.
"""

import os
import logging
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
from typing import Dict, List, Any, Optional, Set, Tuple

class DiagramGenerator:
    """Generates network diagrams from discovered topology."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the DiagramGenerator with an optional logger."""
        self.logger = logger or logging.getLogger(__name__)
        self.graph = nx.Graph()
        
    def build_graph(self, devices: Dict[str, Dict[str, Any]]) -> None:
        """
        Build a graph representation of the network topology.
        
        Args:
            devices: Dictionary of devices and their information
        """
        # Clear existing graph
        self.graph.clear()
        
        # Add nodes (devices)
        for device_ip, device_data in devices.items():
            hostname = device_data.get('hostname', device_ip)
            device_type = self._determine_device_type(device_data)
            
            self.graph.add_node(device_ip, 
                               label=hostname, 
                               device_type=device_type,
                               data=device_data)
            
        # Add edges (connections)
        added_connections = set()  # Track added connections to avoid duplicates
        
        for source_ip, device_data in devices.items():
            if 'neighbors' in device_data:
                for neighbor in device_data['neighbors']:
                    neighbor_ip = neighbor.get('ip')
                    
                    if neighbor_ip and neighbor_ip in devices:
                        # Create a unique connection identifier
                        connection_id = tuple(sorted([source_ip, neighbor_ip]))
                        
                        if connection_id not in added_connections:
                            # Get interface information
                            local_intf = neighbor.get('local_interface', '')
                            remote_intf = neighbor.get('remote_interface', '')
                            
                            self.graph.add_edge(source_ip, neighbor_ip, 
                                              local_interface=local_intf,
                                              remote_interface=remote_intf)
                            
                            added_connections.add(connection_id)
        
        self.logger.info(f"Built graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
    
    def _determine_device_type(self, device_data: Dict[str, Any]) -> str:
        """
        Determine the type of device based on available information.
        
        Args:
            device_data: Dictionary containing device information
            
        Returns:
            String representing the device type
        """
        # Try to determine from model or other attributes
        hardware = device_data.get('hardware', '').lower()
        hostname = device_data.get('hostname', '').lower()
        
        if any(sw_type in hardware for sw_type in ['cat', '2960', '3750', '9300']):
            return 'switch'
        elif any(rt_type in hardware for rt_type in ['isr', '4300', '4400', '1900', '2900', '3900']):
            return 'router'
        elif any(fw_type in hardware for fw_type in ['asa', 'firepower']):
            return 'firewall'
        elif 'sw' in hostname:
            return 'switch'
        elif 'rt' in hostname or 'rtr' in hostname:
            return 'router'
        elif 'fw' in hostname:
            return 'firewall'
        
        # Default to switch if can't determine
        return 'switch'
    
    def generate_matplotlib_diagram(self, output_file: str, 
                                   filter_types: Optional[List[str]] = None) -> None:
        """
        Generate a network diagram using matplotlib.
        
        Args:
            output_file: Path to save the output image
            filter_types: List of device types to include (None for all)
        """
        filtered_graph = self._apply_filters(filter_types)
        
        plt.figure(figsize=(12, 10))
        
        # Define positions using spring layout
        pos = nx.spring_layout(filtered_graph, seed=42)
        
        # Draw nodes by device type with different colors
        device_types = nx.get_node_attributes(filtered_graph, 'device_type')
        
        # Define colors for different device types
        color_map = {
            'router': 'red',
            'switch': 'green',
            'firewall': 'orange',
            'unknown': 'gray'
        }
        
        # Draw nodes grouped by device type
        for device_type, color in color_map.items():
            nodes = [node for node, type_val in device_types.items() if type_val == device_type]
            nx.draw_networkx_nodes(filtered_graph, pos, nodelist=nodes, node_color=color, node_size=500, alpha=0.8)
        
        # Draw edges
        nx.draw_networkx_edges(filtered_graph, pos, width=1.0, alpha=0.5)
        
        # Draw labels
        labels = nx.get_node_attributes(filtered_graph, 'label')
        nx.draw_networkx_labels(filtered_graph, pos, labels=labels, font_size=8)
        
        # Draw edge labels (interfaces)
        edge_labels = {}
        for u, v, data in filtered_graph.edges(data=True):
            local_intf = data.get('local_interface', '')
            remote_intf = data.get('remote_interface', '')
            
            if local_intf and remote_intf:
                edge_labels[(u, v)] = f"{local_intf} - {remote_intf}"
        
        nx.draw_networkx_edge_labels(filtered_graph, pos, edge_labels=edge_labels, font_size=6)
        
        # Add legend
        legend_elements = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10, label=device_type)
                          for device_type, color in color_map.items() if any(t == device_type for t in device_types.values())]
        
        plt.legend(handles=legend_elements, loc='upper right')
        
        plt.title("Network Topology")
        plt.axis('off')
        plt.tight_layout()
        
        # Save figure
        directory = os.path.dirname(output_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        self.logger.info(f"Saved matplotlib diagram to {output_file}")
        plt.close()
    
    def generate_interactive_diagram(self, output_file: str, 
                                    filter_types: Optional[List[str]] = None) -> None:
        """
        Generate an interactive HTML network diagram using pyvis.
        
        Args:
            output_file: Path to save the output HTML file
            filter_types: List of device types to include (None for all)
        """
        filtered_graph = self._apply_filters(filter_types)
        
        # Create pyvis network
        net = Network(height="900px", width="100%", notebook=False, directed=False)
        
        # Define colors for different device types
        color_map = {
            'router': '#FF6666',  # light red
            'switch': '#66CC66',  # light green
            'firewall': '#FFA500', # orange
            'unknown': '#CCCCCC'  # light gray
        }
        
        # Add nodes with proper attributes
        for node, attr in filtered_graph.nodes(data=True):
            device_type = attr.get('device_type', 'unknown')
            label = attr.get('label', node)
            device_data = attr.get('data', {})
            
            # Build a title (tooltip) with more info
            title = f"<b>{label}</b><br>"
            title += f"IP: {node}<br>"
            title += f"Type: {device_type}<br>"
            if 'version' in device_data:
                title += f"Version: {device_data['version']}<br>"
            if 'hardware' in device_data:
                title += f"Model: {device_data['hardware']}<br>"
            
            net.add_node(node, 
                         label=label, 
                         title=title,
                         color=color_map.get(device_type, color_map['unknown']))
        
        # Add edges with interface information
        for u, v, data in filtered_graph.edges(data=True):
            local_intf = data.get('local_interface', '')
            remote_intf = data.get('remote_interface', '')
            
            title = f"{local_intf} ⟷ {remote_intf}" if local_intf and remote_intf else ""
            
            net.add_edge(u, v, title=title)
        
        # Configure physics
        net.barnes_hut(spring_length=200)
        
        # Add filter control buttons
        net.show_buttons(filter_=['physics'])
        
        # Save the visualization
        directory = os.path.dirname(output_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        net.save_graph(output_file)
        self.logger.info(f"Saved interactive diagram to {output_file}")
    
    def _apply_filters(self, filter_types: Optional[List[str]] = None) -> nx.Graph:
        """
        Apply filters to the graph and return a filtered copy.
        
        Args:
            filter_types: List of device types to include (None for all)
            
        Returns:
            Filtered networkx graph
        """
        if not filter_types:
            return self.graph.copy()
        
        # Create a subgraph with only the specified device types
        filtered_nodes = [node for node, attr in self.graph.nodes(data=True) 
                         if attr.get('device_type') in filter_types]
        
        return self.graph.subgraph(filtered_nodes).copy()