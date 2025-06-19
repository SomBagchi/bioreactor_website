# Bioreactor Hub

Middleware service for hardware abstraction and experiment orchestration.

## Purpose

The bioreactor-hub component acts as a middleware between the web server and the bioreactor hardware. It manages user experiment containers, provides hardware abstraction APIs, and handles communication with the bioreactor-node.

## Features

- **Hardware Abstraction**: REST API proxy to bioreactor-node
- **Container Orchestration**: Manage user experiment containers
- **Experiment Management**: Start, stop, and monitor experiments
- **Result Storage**: Store and retrieve experiment results
- **Security**: Isolate user experiments in containers
- **SSH Communication**: Secure communication with bioreactor-node

## Architecture

```
Web Server → SSH → Bioreactor Hub → SSH → Bioreactor Node
User Script → Container → REST API → Bioreactor Hub → SSH → Bioreactor Node
```

## API Endpoints

### Hardware Abstraction
- `GET /api/hardware/status` - Get hardware status
- `POST /api/hardware/control` - Control hardware components
- `GET /api/hardware/sensors` - Get sensor data

### Experiment Management
- `POST /api/experiments/start` - Start new experiment
- `GET /api/experiments/{id}/status` - Get experiment status
- `POST /api/experiments/{id}/stop` - Stop experiment
- `GET /api/experiments/{id}/results` - Get experiment results
- `DELETE /api/experiments/{id}` - Delete experiment

### Container Management
- `GET /api/containers` - List running containers
- `GET /api/containers/{id}/logs` - Get container logs
- `POST /api/containers/{id}/stop` - Stop container

## Container Security

### User Experiment Containers
- **Base Image**: Python 3.9+ with restricted packages
- **Allowed Packages**: numpy, pandas, matplotlib, scikit-learn
- **Network Access**: Only to bioreactor-hub API
- **File System**: Read-only except for output directory
- **Resource Limits**: CPU, memory, disk usage limits

### Security Features
- **Package Whitelist**: Only approved Python packages
- **Network Isolation**: Containers can only communicate with hub API
- **File System Restrictions**: No access to host system
- **Resource Limits**: Prevent resource exhaustion
- **Time Limits**: Maximum experiment duration

## Deployment

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- SSH access to bioreactor-node
- Sufficient storage for experiment results

### Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd bioreactor_website/bioreactor-hub

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your settings

# Run the server
python -m src.main
```

### Docker Deployment
```bash
# Build and run with Docker
docker build -t bioreactor-hub .
docker run -d --name bioreactor-hub -p 8000:8000 bioreactor-hub
```

## Configuration

### Environment Variables
- `BIOREACTOR_NODE_HOST`: Hostname of bioreactor-node
- `BIOREACTOR_NODE_PORT`: SSH port for bioreactor-node
- `SSH_KEY_PATH`: Path to SSH private key
- `EXPERIMENT_DATA_DIR`: Directory for storing experiment results
- `MAX_EXPERIMENT_DURATION`: Maximum experiment duration in seconds
- `CONTAINER_MEMORY_LIMIT`: Memory limit for containers (e.g., "512m")

### Container Configuration
Edit `docker/user-experiment/Dockerfile` to:
- Change base Python image
- Modify allowed packages
- Adjust security settings

## Experiment Lifecycle

1. **Upload**: User uploads script to web server
2. **Validation**: Hub validates script and creates container
3. **Execution**: Container runs script, communicates via API
4. **Monitoring**: Hub monitors container and experiment status
5. **Completion**: Results stored, container cleaned up
6. **Download**: User downloads results

## Storage

### Experiment Results
- **Location**: `/app/data/experiments/{experiment_id}/`
- **Contents**: 
  - `output/` - User script output files
  - `stdout.txt` - Standard output
  - `stderr.txt` - Standard error
  - `exitcode.txt` - Exit code
  - `results.zip` - Compressed results for download

### Data Retention
- **Active Experiments**: Kept until user downloads
- **Completed Experiments**: Configurable retention period
- **Failed Experiments**: Kept for debugging

## Development

### Local Development
```bash
# Run in development mode
export FLASK_ENV=development
python -m src.main
```

### Testing
```bash
# Run tests
pytest tests/

# Test container creation
python -m src.containers.test_container
```

## Monitoring

### Health Checks
- `GET /health` - Service health status
- `GET /metrics` - Prometheus metrics (if enabled)

### Logging
- Application logs: `/var/log/bioreactor-hub/`
- Container logs: Available via API
- Experiment logs: Stored with results

## Troubleshooting

1. **Container creation fails**: Check Docker daemon and resource limits
2. **SSH connection issues**: Verify SSH keys and network connectivity
3. **API communication errors**: Check bioreactor-node status
4. **Storage issues**: Verify disk space and permissions 
