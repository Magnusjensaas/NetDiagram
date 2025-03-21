# Network Topology Discovery and Visualization Tool

A Python-based tool for discovering and visualizing Cisco network topologies by connecting to devices, gathering information using show commands, and generating interactive diagrams.

## Features

- **Device Discovery**: Connects to Cisco devices and runs show commands to gather information
- **Recursive Discovery**: Finds neighboring devices automatically using CDP/LLDP
- **Network Visualization**: Creates both static and interactive network diagrams
- **Web Interface**: Provides a simple web UI for viewing and filtering diagrams
- **Filtering Capabilities**: Allows showing/hiding devices by type

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/network-discovery.git
   cd network-discovery
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Edit the `sample_devices.yaml` file to include your seed devices:
   ```yaml
   - ip: 192.168.1.1
     device_type: cisco_ios
     username: admin
     password: your_password
     secret: your_enable_secret
   
   - ip: 192.168.2.1
     device_type: cisco_ios
     username: admin
     password: your_password
   ```

2. Customize discovery parameters in the command line arguments.

## Usage

### Basic Usage

```bash
python network_discovery.py
```

This will use the default `sample_devices.yaml` file and store outputs in the `output` directory.

### Advanced Usage

```bash
python network_discovery.py --devices my_devices.yaml --output-dir my_outputs --max-devices 50 --ignore-subnets 10.0.0.0/8 172.16.0.0/12 --web
```

### Command Line Arguments

- `--devices`, `-d`: Path to YAML file containing device information (default: sample_devices.yaml)
- `--output-dir`, `-o`: Directory to store output files (default: output)
- `--max-devices`, `-m`: Maximum number of devices to discover (default: 100)
- `--ignore-subnets`, `-i`: Subnets to ignore during discovery (CIDR format)
- `--web`, `-w`: Start web interface after discovery
- `--web-port`, `-p`: Port for web interface (default: 5000)
- `--verbose`, `-v`: Enable verbose logging

## Web Interface

When the `--web` flag is used, a simple web interface is started at http://localhost:5000 (or the specified port). This interface allows you to:

1. View the generated network diagrams
2. Toggle between different diagram versions
3. Filter the diagram by device type
4. Interact with the diagram (when viewing interactive HTML diagrams)

## Output

The tool generates the following outputs in the specified output directory:

1. **Discovery YAML**: Raw discovery data in YAML format
2. **Static PNG Diagram**: Network topology diagram as a PNG image
3. **Interactive HTML Diagram**: Interactive network diagram as an HTML file

## Security Considerations

- Credentials are stored in plaintext in the YAML file. Consider using environment variables or a secure credential store in production.
- The web interface is intended for local use. Additional security measures should be implemented if exposing it over a network.

## Troubleshooting

- **Connection Issues**: Check device credentials and ensure network connectivity
- **Parse Errors**: The tool uses pattern matching to parse command outputs, which might fail with unexpected output formats
- **Memory Issues**: Discovering large networks may consume significant memory. Use the `--max-devices` option to limit discovery

## Dependencies

Major dependencies include:
- netmiko: For SSH connections to network devices
- pyyaml: For YAML file parsing
- matplotlib and networkx: For static diagram generation
- pyvis: For interactive HTML diagrams
- flask: For the web interface

## License

This project is licensed under the MIT License - see the LICENSE file for details.