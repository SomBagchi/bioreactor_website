"""
Bioreactor Hub - Experiment Forwarding Service
Forwards experiment scripts to bioreactor-node for execution.
"""

import os
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional, Any

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import uvicorn

from .ssh_client import BioreactorNodeClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
node_client: Optional[BioreactorNodeClient] = None

# Pydantic models
class ExperimentRequest(BaseModel):
    script_content: str
    config: Optional[Dict[str, Any]] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global node_client
    
    # Startup
    logger.info("Starting Bioreactor Hub...")
    
    # Initialize SSH client for bioreactor-node
    node_host = os.getenv("BIOREACTOR_NODE_HOST", "localhost")
    node_port = int(os.getenv("BIOREACTOR_NODE_PORT", "22"))
    node_username = os.getenv("BIOREACTOR_NODE_USERNAME", "pi")
    ssh_key_path = os.getenv("SSH_KEY_PATH")
    
    node_client = BioreactorNodeClient(
        host=node_host,
        port=node_port,
        username=node_username,
        key_path=ssh_key_path
    )
    
    # Test SSH connection
    if node_client.connect():
        logger.info(f"SSH connection to bioreactor-node established")
    else:
        logger.warning("Failed to establish SSH connection to bioreactor-node")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Bioreactor Hub...")
    if node_client:
        node_client.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Bioreactor Hub API",
    description="Experiment forwarding service to bioreactor-node",
    version="1.0.0",
    lifespan=lifespan
)




# Dependency functions
def get_node_client() -> BioreactorNodeClient:
    if node_client is None:
        raise HTTPException(status_code=503, detail="Node client not available")
    return node_client

# Experiment management endpoints
@app.post("/api/experiments/start")
async def start_experiment(
    request: ExperimentRequest,
    client: BioreactorNodeClient = Depends(get_node_client)
):
    """Start a new experiment by forwarding script to bioreactor-node"""
    try:
        # Generate experiment ID
        experiment_id = str(uuid.uuid4())
        
        # Forward experiment to node
        result = client.forward_experiment(experiment_id, request.script_content)
        
        if result["success"]:
            return {
                "experiment_id": experiment_id,
                "status": "started",
                "message": "Experiment forwarded to bioreactor-node"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start experiment: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Failed to start experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments/{experiment_id}/status")
async def get_experiment_status(
    experiment_id: str,
    client: BioreactorNodeClient = Depends(get_node_client)
):
    """Get experiment status from bioreactor-node"""
    try:
        return client.get_experiment_status(experiment_id)
    except Exception as e:
        logger.error(f"Failed to get experiment status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 
