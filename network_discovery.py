#!/usr/bin/env python3
"""
Main module for Cisco network discovery tool.
Discovers network topology and generates diagrams.
"""

import os
import sys
import yaml
import logging
import argparse
from typing import Dict, List, Any, Optional
import ipaddress
from datetime import datetime

from device_connector import DeviceConnector
from data_parser import DataParser
from diagram_generator import DiagramGenerator
from web_interface import WebInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('network_discovery.log')
    ]
)

logger = logging.getLogger(__name__)

def load_device_list(file_path: str) -> List[Dict[str, Any]]:
    """
    Load the device list from a YAML file.
    
    Args:
        file_path: Path to the YAML file containing device information
        
    Returns:
        List of device dictionaries
    """
    try:
        with open(file_path, 'r') as f:
            devices = yaml.safe_load(f)
        return devices
    except Exception as e:
        logger.error(f"Error loading device list from {file_path}: {str(e)}")
        sys.exit(1)

def discover_single_device(connector: DeviceConnector, parser: DataParser, 
                          device_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Discover a single device and its neighbors.
    
    Args:
        connector: DeviceConnector instance
        parser: DataParser instance
        device_params: Dictionary of device connection parameters
        
    Returns:
        Dictionary of device information
    """
    device_ip = device_params.get('ip', 'unknown')
    logger.info(f"Starting discovery for device: {device_ip}")
    
    device_data = {
        'ip': device_ip,
        'discovered_at': datetime.now().isoformat()
    }
    
    # Connect to the device
    connection = connector.connect(device_params)
    if not connection:
        logger.error(f"Failed to connect to {device_ip}. Skipping...")
        return device_data
    
    try:
        # Run discovery commands
        commands = [
            'show version',
            'show cdp neighbors detail',
            'show lldp neighbors detail',
            'show interfaces',
            'show ip interface brief',
            'show vlan brief',
            'show spanning-tree bridge',
            'show ip route'
        ]
        
        results = connector.execute_commands(connection, commands)
        
        # Parse version information
        version_data = parser.parse_version(results.get('show version', ''))
        device_data.update(version_data)
        
        # Parse CDP neighbors
        cdp_neighbors = parser.parse_cdp_neighbors(results.get('show cdp neighbors detail', ''))
        
        # Parse LLDP neighbors (and combine with CDP)
        lldp_neighbors = parser.parse_lldp_neighbors(results.get('show lldp neighbors detail', ''))
        
        # Combine neighbors and remove duplicates based on IP
        all_neighbors = cdp_neighbors.copy()
        
        # Track IPs to avoid duplicates
        neighbor_ips = {n.get('ip') for n in all_neighbors if n.get('ip')}
        
        for lldp_neighbor in lldp_neighbors:
            if lldp_neighbor.get('ip') not in neighbor_ips:
                all_neighbors.append(lldp_neighbor)
                neighbor_ips.add(lldp_neighbor.get('ip'))
        
        device_data['neighbors'] = all_neighbors
        
        # Parse interfaces
        interfaces = parser.parse_interfaces(results.get('show interfaces', ''))
        device_data['interfaces'] = interfaces
        
        # Add the raw command results for reference/troubleshooting
        device_data['raw_output'] = results
        
        logger.info(f"Discovered {device_ip} with {len(all_neighbors)} neighbors")
        
    except Exception as e:
        logger.error(f"Error discovering device {device_ip}: {str(e)}")
    finally:
        connector.disconnect(connection)
    
    return device_data

def discover_network(seed_devices: List[Dict[str, Any]], 
                    max_devices: int = 100, 
                    ignore_subnets: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Discover the network topology starting from seed devices.
    
    Args:
        seed_devices: List of seed devices to start discovery from
        max_devices: Maximum number of devices to discover
        ignore_subnets: List of subnet CIDRs to ignore
        
    Returns:
        Dictionary mapping device IPs to their information
    """
    logger.info(f"Starting network discovery with {len(seed_devices)} seed devices")
    
    # Initialize components
    connector = DeviceConnector(logger)
    parser = DataParser(logger)
    
    # Track discovered devices
    discovered_devices = {}
    discovery_queue = seed_devices.copy()
    attempted_ips = set()
    
    # Prepare ignore subnets
    ignored_networks = []
    if ignore_subnets:
        for subnet in ignore_subnets:
            try:
                ignored_networks.append(ipaddress.ip_network(subnet))
            except ValueError:
                logger.warning(f"Invalid subnet format: {subnet}")
    
    # Process devices in the queue
    while discovery_queue and len(discovered_devices) < max_devices:
        device_params = discovery_queue.pop(0)
        device_ip = device_params.get('ip')
        
        if device_ip in attempted_ips:
            continue
            
        # Check if the device is in an ignored subnet
        try:
            ip_addr = ipaddress.ip_address(device_ip)
            if any(ip_addr in network for network in ignored_networks):
                logger.info(f"Skipping {device_ip} as it's in an ignored subnet")
                attempted_ips.add(device_ip)
                continue
        except ValueError:
            logger.warning(f"Invalid IP format: {device_ip}")
            attempted_ips.add(device_ip)
            continue
        
        # Discover the device
        device_data = discover_single_device(connector, parser, device_params)
        discovered_devices[device_ip] = device_data
        attempted_ips.add(device_ip)
        
        # Process neighbors for recursive discovery
        if 'neighbors' in device_data:
            for neighbor in device_data['neighbors']:
                neighbor_ip = neighbor.get('ip')
                if (neighbor_ip and 
                    neighbor_ip not in attempted_ips and 
                    neighbor_ip not in [d.get('ip') for d in discovery_queue]):
                    
                    # Check if the neighbor is in an ignored subnet
                    try:
                        ip_addr = ipaddress.ip_address(neighbor_ip)
                        if any(ip_addr in network for network in ignored_networks):
                            logger.info(f"Skipping neighbor {neighbor_ip} as it's in an ignored subnet")
                            continue
                    except ValueError:
                        logger.warning(f"Invalid neighbor IP format: {neighbor_ip}")
                        continue
                    
                    # Add to discovery queue with same credentials as parent
                    neighbor_params = device_params.copy()
                    neighbor_params['ip'] = neighbor_ip
                    discovery_queue.append(neighbor_params)
    
    logger.info(f"Discovery complete. Found {len(discovered_devices)} devices.")
    return discovered_devices

def main():
    """Main function to run the network discovery tool."""
    parser = argparse.ArgumentParser(description='Cisco Network Discovery Tool')
    parser.add_argument('--devices', '-d', default='sample_devices.yaml',
                      help='Path to YAML file containing device information')
    parser.add_argument('--output-dir', '-o', default='output',
                      help='Directory to store output files')
    parser.add_argument('--max-devices', '-m', type=int, default=100,
                      help='Maximum number of devices to discover')
    parser.add_argument('--ignore-subnets', '-i', nargs='+',
                      help='Subnets to ignore during discovery (CIDR format)')
    parser.add_argument('--web', '-w', action='store_true',
                      help='Start web interface after discovery')
    parser.add_argument('--web-port', '-p', type=int, default=5000,
                      help='Port for web interface')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Ensure output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Load device list
    seed_devices = load_device_list(args.devices)
    
    # Discover the network
    devices = discover_network(
        seed_devices=seed_devices,
        max_devices=args.max_devices,
        ignore_subnets=args.ignore_subnets
    )
    
    # Save discovery results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    discovery_file = os.path.join(args.output_dir, f'discovery_{timestamp}.yaml')
    
    try:
        with open(discovery_file, 'w') as f:
            # Remove raw output to keep file size manageable
            clean_devices = {}
            for ip, data in devices.items():
                clean_data = data.copy()
                if 'raw_output' in clean_data:
                    del clean_data['raw_output']
                clean_devices[ip] = clean_data
                
            yaml.dump(clean_devices, f, default_flow_style=False)
        logger.info(f"Saved discovery results to {discovery_file}")
    except Exception as e:
        logger.error(f"Error saving discovery results: {str(e)}")
    
    # Generate diagrams
    diagram_generator = DiagramGenerator(logger)
    diagram_generator.build_graph(devices)
    
    # Static diagram
    static_diagram_file = os.path.join(args.output_dir, f'topology_{timestamp}.png')
    diagram_generator.generate_matplotlib_diagram(static_diagram_file)
    
    # Interactive diagram
    interactive_diagram_file = os.path.join(args.output_dir, f'topology_{timestamp}.html')
    diagram_generator.generate_interactive_diagram(interactive_diagram_file)
    
    logger.info("Diagram generation complete")
    
    # Start web interface if requested
    if args.web:
        web_ui = WebInterface(args.output_dir, logger)
        web_ui.set_device_data(devices)
        web_ui.run(port=args.web_port)

if __name__ == '__main__':
    main()