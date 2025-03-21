#!/usr/bin/env python3
"""
Data parser module for Cisco network discovery tool.
Parses output from show commands to extract structured data.
"""

import re
import logging
from typing import Dict, List, Any, Optional

class DataParser:
    """Parses raw command outputs into structured data."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the DataParser with an optional logger."""
        self.logger = logger or logging.getLogger(__name__)
    
    def parse_cdp_neighbors(self, output: str) -> List[Dict[str, str]]:
        """
        Parse the output of 'show cdp neighbors detail' command.
        
        Args:
            output: String output from the command
            
        Returns:
            List of dictionaries containing neighbor information
        """
        neighbors = []
        
        # If output is already parsed by TextFSM
        if isinstance(output, list):
            return output
        
        # Manual parsing for cases where TextFSM fails
        device_blocks = re.split(r'-{3,}', output)
        
        for block in device_blocks:
            if not block.strip():
                continue
                
            neighbor = {}
            
            # Extract device ID
            device_id_match = re.search(r'Device ID:[\s]*(.+?)[\r\n]', block)
            if device_id_match:
                neighbor['device_id'] = device_id_match.group(1).strip()
            
            # Extract IP address
            ip_match = re.search(r'IP(?:v4)? address:[\s]*(.+?)[\r\n]', block)
            if ip_match:
                neighbor['ip'] = ip_match.group(1).strip()
                
            # Extract platform
            platform_match = re.search(r'Platform:[\s]*(.+?),', block)
            if platform_match:
                neighbor['platform'] = platform_match.group(1).strip()
                
            # Extract interface information
            local_int_match = re.search(r'Interface:[\s]*(.+?),', block)
            remote_int_match = re.search(r'Port ID \(outgoing port\):[\s]*(.+?)[\r\n]', block)
            
            if local_int_match:
                neighbor['local_interface'] = local_int_match.group(1).strip()
            if remote_int_match:
                neighbor['remote_interface'] = remote_int_match.group(1).strip()
                
            # Only add if we have essential information
            if neighbor.get('device_id') and neighbor.get('ip'):
                neighbors.append(neighbor)
        
        return neighbors
    
    def parse_lldp_neighbors(self, output: str) -> List[Dict[str, str]]:
        """
        Parse the output of 'show lldp neighbors detail' command.
        
        Args:
            output: String output from the command
            
        Returns:
            List of dictionaries containing neighbor information
        """
        # If output is already parsed by TextFSM
        if isinstance(output, list):
            return output
        
        neighbors = []
        # Similar parsing logic to CDP but adapted for LLDP format
        # This is a simplified version - would need enhancement for production
        
        device_blocks = re.split(r'[\r\n][\r\n]Device ID:.+?[\r\n]', output)
        
        for block in device_blocks:
            if not block.strip():
                continue
                
            neighbor = {}
            
            # Extract device ID
            device_id_match = re.search(r'System Name:[\s]*(.+?)[\r\n]', block)
            if device_id_match:
                neighbor['device_id'] = device_id_match.group(1).strip()
            
            # Extract IP address
            ip_match = re.search(r'Management Address:[\s]*(.+?)[\r\n]', block)
            if ip_match:
                neighbor['ip'] = ip_match.group(1).strip()
                
            # Extract interface information
            local_int_match = re.search(r'Local Interface:[\s]*(.+?)[\r\n]', block)
            remote_int_match = re.search(r'Port ID:[\s]*(.+?)[\r\n]', block)
            
            if local_int_match:
                neighbor['local_interface'] = local_int_match.group(1).strip()
            if remote_int_match:
                neighbor['remote_interface'] = remote_int_match.group(1).strip()
                
            # Only add if we have essential information
            if neighbor.get('device_id') and neighbor.get('ip'):
                neighbors.append(neighbor)
        
        return neighbors
    
    def parse_interfaces(self, output: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse the output of 'show interfaces' command.
        
        Args:
            output: String output from the command
            
        Returns:
            Dictionary of interfaces with their details
        """
        # If output is already parsed by TextFSM
        if isinstance(output, list):
            interface_dict = {}
            for intf in output:
                interface_dict[intf.get('interface', 'unknown')] = intf
            return interface_dict
        
        # Manual parsing logic would go here
        return {}
    
    def parse_version(self, output: str) -> Dict[str, Any]:
        """
        Parse the output of 'show version' command.
        
        Args:
            output: String output from the command
            
        Returns:
            Dictionary containing version and hardware information
        """
        # If output is already parsed by TextFSM
        if isinstance(output, dict) or isinstance(output, list):
            if isinstance(output, list) and len(output) > 0:
                return output[0]
            return output
        
        # Manual parsing for when TextFSM fails
        version_info = {}
        
        # Extract model
        model_match = re.search(r'(?:cisco|Cisco)\s+(\S+)(?:\s+\S+){0,3}\s+processor', output)
        if model_match:
            version_info['hardware'] = model_match.group(1)
        
        # Extract IOS version
        version_match = re.search(r'Cisco IOS Software.*Version\s+([^,\s]+)', output)
        if version_match:
            version_info['version'] = version_match.group(1)
        
        # Extract hostname
        hostname_match = re.search(r'(\S+)\s+uptime\s+is', output)
        if hostname_match:
            version_info['hostname'] = hostname_match.group(1)
            
        return version_info