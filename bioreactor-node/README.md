# Bioreactor Node

Direct hardware interface running on bioreactor hardware.

## Purpose

The bioreactor-node component provides a REST API interface to the actual bioreactor hardware. It runs directly on the bioreactor hardware and exposes all hardware functionality through a secure API.

## Features

- **Hardware Abstraction**: REST API for all bioreactor functions
- **SSH Server**: Secure communication with bioreactor-hub
- **Hardware Drivers**: Direct interface with GPIO, I2C, USB devices
- **Status Monitoring**: Real-time hardware status
- **Security**: No direct user access to hardware

## Hardware Interfaces

- **GPIO**: LEDs, stirrer, peltier control
- **I2C**: ADC for photodiodes, temperature sensors, current sensors
- **USB**: Pump control via TicUSB
- **SPI**: Additional sensors
- **Temperature Sensors**: DS18B20 sensors for vial temperatures

## API Endpoints

### Hardware Control
- `GET /api/status` - Get hardware status
- `POST /api/led` - Control LED
- `POST /api/ring-light` - Control ring light
- `POST /api/peltier` - Control peltier (temperature)
- `POST /api/pump` - Control pumps
- `POST /api/stirrer` - Control stirrer

### Sensor Data
- `GET /api/sensors/photodiodes` - Get photodiode readings
- `GET /api/sensors/temperature` - Get temperature readings
- `GET /api/sensors/current` - Get current readings

### Experiment Management
- `POST /api/experiment/start` - Start experiment
- `POST /api/experiment/stop` - Stop experiment
- `GET /api/experiment/status` - Get experiment status

## Deployment

### Prerequisites
- Raspberry Pi or similar single-board computer
- Bioreactor hardware connected
- Python 3.9+
- Required hardware libraries (RPi.GPIO, adafruit libraries, etc.)

### Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd bioreactor_website/bioreactor-node

# Install dependencies
pip install -r requirements.txt

# Configure hardware settings in config.py
# Set HARDWARE_MODE=real in environment

# Run the server
python -m src.main
```

### Docker Deployment
```bash
# Build and run with Docker
docker build -t bioreactor-node .
docker run -d --name bioreactor-node --privileged -p 9000:9000 bioreactor-node
```

## Configuration

Edit `src/config.py` to configure:
- GPIO pin assignments
- I2C addresses
- Pump serial numbers
- Sensor configurations

## Security

- SSH server for secure communication
- API authentication (to be implemented)
- Hardware access restrictions
- Network isolation

## Development

### Local Development (Simulation Mode)
```bash
export HARDWARE_MODE=simulation
python -m src.main
```

### Hardware Testing
```bash
export HARDWARE_MODE=real
python -m src.main
```

## Troubleshooting

1. **Hardware not detected**: Check connections and I2C addresses
2. **Permission errors**: Ensure proper GPIO access permissions
3. **SSH connection issues**: Verify SSH keys and network connectivity
4. **API errors**: Check hardware initialization in logs 
