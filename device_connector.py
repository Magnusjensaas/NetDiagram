#!/usr/bin/env python3
"""
Device connector module for Cisco network discovery tool.
Handles SSH connections and command execution on network devices.
"""

import logging
import time
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from typing import List, Dict, Any, Optional

class DeviceConnector:
    """Handles connections to network devices and executes commands."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the DeviceConnector with an optional logger."""
        self.logger = logger or logging.getLogger(__name__)
    
    def connect(self, device_params: Dict[str, Any]) -> Optional[ConnectHandler]:
        """
        Establish a connection to a network device.
        
        Args:
            device_params: Dictionary with device connection parameters
                          (device_type, ip, username, password, etc.)
        
        Returns:
            ConnectHandler object if successful, None otherwise
        """
        try:
            self.logger.info(f"Connecting to {device_params.get('ip', 'Unknown device')}")
            connection = ConnectHandler(**device_params)
            self.logger.info(f"Successfully connected to {device_params.get('ip')}")
            return connection
        except NetmikoTimeoutException:
            self.logger.error(f"Connection timeout to {device_params.get('ip')}")
        except NetmikoAuthenticationException:
            self.logger.error(f"Authentication failed for {device_params.get('ip')}")
        except Exception as e:
            self.logger.error(f"Failed to connect to {device_params.get('ip')}: {str(e)}")
        return None
    
    def execute_commands(self, connection: ConnectHandler, commands: List[str], 
                         parse_output: bool = False) -> Dict[str, str]:
        """
        Execute a list of commands on a connected device.
        
        Args:
            connection: Active ConnectHandler object
            commands: List of commands to execute
            parse_output: Whether to attempt to use TextFSM parsing
            
        Returns:
            Dictionary mapping each command to its output
        """
        results = {}
        
        for command in commands:
            try:
                self.logger.debug(f"Executing command: {command}")
                if parse_output:
                    output = connection.send_command(command, use_textfsm=True)
                else:
                    output = connection.send_command(command)
                results[command] = output
                time.sleep(0.5)  # Small delay to prevent overwhelming the device
            except Exception as e:
                self.logger.error(f"Error executing '{command}': {str(e)}")
                results[command] = f"ERROR: {str(e)}"
        
        return results
    
    def disconnect(self, connection: ConnectHandler) -> None:
        """
        Properly disconnect from a network device.
        
        Args:
            connection: Active ConnectHandler object
        """
        try:
            connection.disconnect()
            self.logger.info("Successfully disconnected from device")
        except Exception as e:
            self.logger.error(f"Error during disconnect: {str(e)}")