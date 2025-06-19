# Bioreactor System Deployment Guide

This guide explains how to deploy the three components of the bioreactor system.

## Prerequisites

- Docker and Docker Compose installed
- SSH access between machines
- Python 3.9+ (for local development)

## Component Overview

1. **bioreactor-node**: Runs on the actual bioreactor hardware
2. **bioreactor-hub**: Runs on an intermediate server
3. **web-server**: Runs on your local machine or cloud server

## Quick Start (Local Development)

For local development and testing, you can run all components using Docker Compose:

```bash
# Clone the repository
git clone <your-repo-url>
cd bioreactor_website

# Build and run all components
docker-compose up --build

# The services will be available at:
# - Web Server: http://localhost:5000
# - Bioreactor Hub: http://localhost:8000
# - Bioreactor Node: http://localhost:9000
```

## Production Deployment

### 1. Deploy Bioreactor Node

The bioreactor-node runs directly on the bioreactor hardware (e.g., Raspberry Pi).

```bash
# On the bioreactor hardware machine
git clone <your-repo-url>
cd bioreactor_website/bioreactor-node

# Build the Docker image
docker build -t bioreactor-node .

# Run in simulation mode (for testing)
docker run -d --name bioreactor-node -p 9000:9000 \
  -e HARDWARE_MODE=simulation \
  bioreactor-node

# Run with real hardware (production)
docker run -d --name bioreactor-node -p 9000:9000 \
  --privileged \
  -e HARDWARE_MODE=real \
  -v /dev:/dev \
  bioreactor-node
```

**Environment Variables:**
- `HARDWARE_MODE`: Set to `real` for actual hardware, `simulation` for testing

### 2. Deploy Bioreactor Hub

The bioreactor-hub runs on an intermediate server that manages experiments and communicates with the bioreactor-node.

```bash
# On the bioreactor-hub machine
git clone <your-repo-url>
cd bioreactor_website/bioreactor-hub

# Build the Docker image
docker build -t bioreactor-hub .

# Create environment file
cat > .env << EOF
BIOREACTOR_NODE_HOST=<bioreactor-node-ip>
BIOREACTOR_NODE_PORT=22
BIOREACTOR_NODE_USERNAME=pi
SSH_KEY_PATH=/app/ssh_keys/id_rsa
EXPERIMENT_DATA_DIR=/app/data
MAX_EXPERIMENT_DURATION=86400
CONTAINER_MEMORY_LIMIT=512m
EOF

# Run the hub
docker run -d --name bioreactor-hub -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/ssh_keys:/app/ssh_keys \
  --env-file .env \
  bioreactor-hub
```

**Environment Variables:**
- `BIOREACTOR_NODE_HOST`: IP address of the bioreactor-node machine
- `BIOREACTOR_NODE_PORT`: SSH port (usually 22)
- `BIOREACTOR_NODE_USERNAME`: SSH username
- `SSH_KEY_PATH`: Path to SSH private key for bioreactor-node access
- `EXPERIMENT_DATA_DIR`: Directory for storing experiment results
- `MAX_EXPERIMENT_DURATION`: Maximum experiment duration in seconds
- `CONTAINER_MEMORY_LIMIT`: Memory limit for user experiment containers

### 3. Deploy Web Server

The web-server provides the user interface for uploading scripts and managing experiments.

```bash
# On your local machine or cloud server
git clone <your-repo-url>
cd bioreactor_website/web-server

# Build the Docker image
docker build -t bioreactor-web-server .

# Create environment file
cat > .env << EOF
BIOREACTOR_HUB_HOST=<bioreactor-hub-ip>
BIOREACTOR_HUB_PORT=22
SSH_KEY_PATH=/app/ssh_keys/id_rsa
UPLOAD_FOLDER=/app/uploads
MAX_CONTENT_LENGTH=10485760
SECRET_KEY=your-secret-key-here
EOF

# Run the web server
docker run -d --name bioreactor-web-server -p 5000:5000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/ssh_keys:/app/ssh_keys \
  --env-file .env \
  bioreactor-web-server
```

**Environment Variables:**
- `BIOREACTOR_HUB_HOST`: IP address of the bioreactor-hub machine
- `BIOREACTOR_HUB_PORT`: SSH port (usually 22)
- `SSH_KEY_PATH`: Path to SSH private key for bioreactor-hub access
- `UPLOAD_FOLDER`: Directory for temporary file uploads
- `MAX_CONTENT_LENGTH`: Maximum file upload size in bytes
- `SECRET_KEY`: Flask secret key for sessions

## SSH Key Setup

### 1. Generate SSH Keys

```bash
# Generate key pair for web-server → bioreactor-hub
ssh-keygen -t rsa -b 4096 -f web_to_hub_key -N ""

# Generate key pair for bioreactor-hub → bioreactor-node
ssh-keygen -t rsa -b 4096 -f hub_to_node_key -N ""
```

### 2. Configure SSH Access

```bash
# Copy web_to_hub_key.pub to bioreactor-hub machine
ssh-copy-id -i web_to_hub_key.pub user@bioreactor-hub-ip

# Copy hub_to_node_key.pub to bioreactor-node machine
ssh-copy-id -i hub_to_node_key.pub user@bioreactor-node-ip
```

### 3. Update Environment Files

Update the SSH key paths in the environment files:

```bash
# In bioreactor-hub .env
SSH_KEY_PATH=/app/ssh_keys/hub_to_node_key

# In web-server .env
SSH_KEY_PATH=/app/ssh_keys/web_to_hub_key
```

## Testing the Deployment

### 1. Test Individual Components

```bash
# Test bioreactor-node
curl http://bioreactor-node-ip:9000/health

# Test bioreactor-hub
curl http://bioreactor-hub-ip:8000/health

# Test web-server
curl http://web-server-ip:5000/health
```

### 2. Run System Tests

```bash
# Run the test script
python test_system.py
```

### 3. Test User Interface

1. Open http://web-server-ip:5000 in your browser
2. Upload a Python script
3. Monitor the experiment
4. Download results

## Security Considerations

### 1. Network Security

- Use firewalls to restrict access to necessary ports only
- Consider using VPN for remote access
- Use HTTPS in production

### 2. SSH Security

- Use key-based authentication only
- Disable password authentication
- Use non-standard SSH ports if possible

### 3. Container Security

- User experiment containers run with restricted permissions
- Only whitelisted Python packages are available
- Containers have limited network access

### 4. Data Security

- Encrypt sensitive data at rest
- Use secure file permissions
- Regular backups of experiment data

## Monitoring and Logging

### 1. Container Logs

```bash
# View logs for each component
docker logs bioreactor-node
docker logs bioreactor-hub
docker logs bioreactor-web-server
```

### 2. Application Logs

Logs are written to:
- `/var/log/bioreactor-node/` (bioreactor-node)
- `/var/log/bioreactor-hub/` (bioreactor-hub)
- `/var/log/bioreactor-web/` (web-server)

### 3. Health Checks

Each component provides health check endpoints:
- `GET /health` - Basic health status
- `GET /api/status` - Detailed status information

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Verify SSH keys are correctly configured
   - Check network connectivity
   - Ensure SSH service is running

2. **Container Creation Failed**
   - Check Docker daemon is running
   - Verify sufficient disk space
   - Check Docker socket permissions

3. **Hardware Not Accessible**
   - Verify hardware mode is set correctly
   - Check hardware connections
   - Review hardware initialization logs

4. **Experiment Failed**
   - Check container logs
   - Verify script syntax
   - Review resource limits

### Debug Commands

```bash
# Check container status
docker ps -a

# View container logs
docker logs <container-name>

# Execute commands in container
docker exec -it <container-name> /bin/bash

# Check network connectivity
docker network ls
docker network inspect <network-name>
```

## Backup and Recovery

### 1. Data Backup

```bash
# Backup experiment data
tar -czf experiment_data_backup.tar.gz /app/data

# Backup configuration files
tar -czf config_backup.tar.gz *.env
```

### 2. Recovery

```bash
# Restore experiment data
tar -xzf experiment_data_backup.tar.gz -C /app/

# Restore configuration
tar -xzf config_backup.tar.gz
```

## Performance Tuning

### 1. Resource Limits

Adjust container resource limits based on your hardware:

```bash
# In docker-compose.yml or docker run commands
--memory=1g
--cpus=2.0
```

### 2. Database Optimization

For production deployments, consider using a proper database for experiment metadata instead of file-based storage.

### 3. Caching

Implement caching for frequently accessed data like sensor readings and experiment status. 
