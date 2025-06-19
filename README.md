# Bioreactor Control System

A distributed system for running user experiments on bioreactor hardware with proper isolation and security.

## Architecture

This project consists of three main components:

### 1. Web Server (`web-server/`)
- **Purpose**: User interface for uploading scripts and managing experiments
- **Technology**: Flask/FastAPI web server
- **Deployment**: Runs on user's local machine or cloud server
- **Features**: 
  - Script upload interface
  - Experiment monitoring
  - Result download
  - SSH communication with bioreactor-hub

### 2. Bioreactor Hub (`bioreactor-hub/`)
- **Purpose**: Middleware service for hardware abstraction and experiment orchestration
- **Technology**: FastAPI server with Docker container management
- **Deployment**: Runs on intermediate server (bioreactor_hub machine)
- **Features**:
  - Hardware abstraction API
  - Experiment container orchestration
  - SSH communication with bioreactor-node
  - Result storage and retrieval

### 3. Bioreactor Node (`bioreactor-node/`)
- **Purpose**: Direct hardware interface running on bioreactor hardware
- **Technology**: FastAPI server with hardware drivers
- **Deployment**: Runs directly on bioreactor hardware (bioreactor_node machine)
- **Features**:
  - Hardware abstraction REST API
  - SSH server for secure communication
  - Hardware drivers and interfaces
  - Status monitoring

## Communication Flow

```
User Upload → Web Server → SSH → Bioreactor Hub → SSH → Bioreactor Node
User Script → Container → REST API → Bioreactor Hub → SSH → Bioreactor Node
```

## Deployment

### For Local Development
```bash
# Clone the entire repository
git clone <your-repo-url>
cd bioreactor_website

# Run all components locally using Docker Compose
docker-compose up
```

### For Production Deployment

#### Deploy Web Server Only
```bash
# Clone and deploy web-server component
git clone <your-repo-url>
cd bioreactor_website/web-server
# Follow web-server deployment instructions
```

#### Deploy Bioreactor Hub Only
```bash
# Clone and deploy bioreactor-hub component
git clone <your-repo-url>
cd bioreactor_website/bioreactor-hub
# Follow bioreactor-hub deployment instructions
```

#### Deploy Bioreactor Node Only
```bash
# Clone and deploy bioreactor-node component
git clone <your-repo-url>
cd bioreactor_website/bioreactor-node
# Follow bioreactor-node deployment instructions
```

## Security Features

- **Container Isolation**: Each user experiment runs in its own Docker container
- **Hardware Abstraction**: Users can only access hardware through controlled APIs
- **Package Restrictions**: Only whitelisted Python packages allowed in user containers
- **Network Isolation**: Containers have limited network access
- **Resource Limits**: CPU, memory, and disk usage limits per experiment

## Development

Each component can be developed independently. See individual README files in each directory for specific development instructions.

## License

[Add your license information here]
