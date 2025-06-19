"""
Bioreactor Hub - Middleware Service
Provides hardware abstraction and experiment orchestration.
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from .containers.manager import ContainerManager, ContainerConfig
from .ssh.client import AsyncBioreactorNodeClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
container_manager: Optional[ContainerManager] = None
node_client: Optional[AsyncBioreactorNodeClient] = None

# Pydantic models
class ExperimentRequest(BaseModel):
    script_content: str
    config: Optional[ContainerConfig] = None

class HardwareControlRequest(BaseModel):
    endpoint: str
    data: Dict[str, Any]

class LEDRequest(BaseModel):
    state: bool

class RingLightRequest(BaseModel):
    color: List[int]
    pixel: Optional[int] = None

class PeltierRequest(BaseModel):
    power: int
    forward: bool

class PumpRequest(BaseModel):
    pump_name: str
    ml_per_sec: float

class StirrerRequest(BaseModel):
    duty_cycle: int

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global container_manager, node_client
    
    # Startup
    logger.info("Starting Bioreactor Hub...")
    
    # Initialize container manager
    data_dir = os.getenv("EXPERIMENT_DATA_DIR", "/app/data")
    container_manager = ContainerManager(data_dir)
    logger.info(f"Container manager initialized with data dir: {data_dir}")
    
    # Initialize SSH client for bioreactor-node
    node_host = os.getenv("BIOREACTOR_NODE_HOST", "localhost")
    node_port = int(os.getenv("BIOREACTOR_NODE_PORT", "22"))
    node_username = os.getenv("BIOREACTOR_NODE_USERNAME", "pi")
    ssh_key_path = os.getenv("SSH_KEY_PATH")
    
    node_client = AsyncBioreactorNodeClient(
        host=node_host,
        port=node_port,
        username=node_username,
        key_path=ssh_key_path
    )
    
    # Test SSH connection
    if await node_client.connect():
        logger.info(f"SSH connection to bioreactor-node established")
    else:
        logger.warning("Failed to establish SSH connection to bioreactor-node")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Bioreactor Hub...")
    if node_client:
        await node_client.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Bioreactor Hub API",
    description="Middleware service for hardware abstraction and experiment orchestration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency functions
def get_container_manager() -> ContainerManager:
    if container_manager is None:
        raise HTTPException(status_code=503, detail="Container manager not available")
    return container_manager

def get_node_client() -> AsyncBioreactorNodeClient:
    if node_client is None:
        raise HTTPException(status_code=503, detail="Node client not available")
    return node_client

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    node_health = "unknown"
    if node_client:
        try:
            health_result = await node_client.check_health()
            node_health = health_result.get("status", "error")
        except Exception as e:
            node_health = f"error: {e}"
    
    return {
        "status": "healthy",
        "container_manager": container_manager is not None,
        "node_client": node_client is not None,
        "node_health": node_health
    }

# Hardware abstraction endpoints
@app.get("/api/hardware/status")
async def get_hardware_status(client: AsyncBioreactorNodeClient = Depends(get_node_client)):
    """Get hardware status from bioreactor-node"""
    try:
        return await client.get_hardware_status()
    except Exception as e:
        logger.error(f"Failed to get hardware status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hardware/sensors")
async def get_sensor_data(client: AsyncBioreactorNodeClient = Depends(get_node_client)):
    """Get sensor data from bioreactor-node"""
    try:
        return await client.get_sensor_data()
    except Exception as e:
        logger.error(f"Failed to get sensor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hardware/control")
async def control_hardware(
    request: HardwareControlRequest,
    client: AsyncBioreactorNodeClient = Depends(get_node_client)
):
    """Control hardware via bioreactor-node"""
    try:
        return await client.control_hardware(request.endpoint, request.data)
    except Exception as e:
        logger.error(f"Failed to control hardware: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Specific hardware control endpoints
@app.post("/api/hardware/led")
async def control_led(
    request: LEDRequest,
    client: AsyncBioreactorNodeClient = Depends(get_node_client)
):
    """Control LED"""
    try:
        return await client.control_led(request.state)
    except Exception as e:
        logger.error(f"Failed to control LED: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hardware/ring-light")
async def control_ring_light(
    request: RingLightRequest,
    client: AsyncBioreactorNodeClient = Depends(get_node_client)
):
    """Control ring light"""
    try:
        return await client.control_ring_light(request.color, request.pixel)
    except Exception as e:
        logger.error(f"Failed to control ring light: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hardware/peltier")
async def control_peltier(
    request: PeltierRequest,
    client: AsyncBioreactorNodeClient = Depends(get_node_client)
):
    """Control peltier"""
    try:
        return await client.control_peltier(request.power, request.forward)
    except Exception as e:
        logger.error(f"Failed to control peltier: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hardware/pump")
async def control_pump(
    request: PumpRequest,
    client: AsyncBioreactorNodeClient = Depends(get_node_client)
):
    """Control pump"""
    try:
        return await client.control_pump(request.pump_name, request.ml_per_sec)
    except Exception as e:
        logger.error(f"Failed to control pump: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hardware/stirrer")
async def control_stirrer(
    request: StirrerRequest,
    client: AsyncBioreactorNodeClient = Depends(get_node_client)
):
    """Control stirrer"""
    try:
        return await client.control_stirrer(request.duty_cycle)
    except Exception as e:
        logger.error(f"Failed to control stirrer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Experiment management endpoints
@app.post("/api/experiments/start")
async def start_experiment(
    request: ExperimentRequest,
    background_tasks: BackgroundTasks,
    cm: ContainerManager = Depends(get_container_manager)
):
    """Start a new experiment"""
    try:
        # Create experiment container
        experiment_id = cm.create_experiment_container(
            request.script_content,
            request.config
        )
        
        # Start experiment in background
        background_tasks.add_task(cm.start_experiment, experiment_id)
        
        return {
            "status": "success",
            "experiment_id": experiment_id,
            "message": "Experiment started"
        }
    except Exception as e:
        logger.error(f"Failed to start experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments")
async def list_experiments(cm: ContainerManager = Depends(get_container_manager)):
    """List all experiments"""
    try:
        return {
            "status": "success",
            "experiments": cm.list_experiments()
        }
    except Exception as e:
        logger.error(f"Failed to list experiments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments/{experiment_id}/status")
async def get_experiment_status(
    experiment_id: str,
    cm: ContainerManager = Depends(get_container_manager)
):
    """Get experiment status"""
    try:
        status = cm.get_experiment_status(experiment_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {"status": "success", "experiment": status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get experiment status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/experiments/{experiment_id}/stop")
async def stop_experiment(
    experiment_id: str,
    cm: ContainerManager = Depends(get_container_manager)
):
    """Stop experiment"""
    try:
        success = cm.stop_experiment(experiment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {"status": "success", "message": "Experiment stopped"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments/{experiment_id}/results")
async def get_experiment_results(
    experiment_id: str,
    cm: ContainerManager = Depends(get_container_manager)
):
    """Get experiment results"""
    try:
        results = cm.get_experiment_results(experiment_id)
        if results is None:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {"status": "success", "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get experiment results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/experiments/{experiment_id}/download")
async def download_experiment_results(
    experiment_id: str,
    cm: ContainerManager = Depends(get_container_manager)
):
    """Download experiment results as ZIP file"""
    try:
        zip_path = cm.create_results_zip(experiment_id)
        if zip_path is None:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        return FileResponse(
            path=str(zip_path),
            filename=f"experiment_{experiment_id}_results.zip",
            media_type="application/zip"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create results ZIP: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/experiments/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    cm: ContainerManager = Depends(get_container_manager)
):
    """Delete experiment"""
    try:
        success = cm.cleanup_experiment(experiment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {"status": "success", "message": "Experiment deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Container management endpoints
@app.get("/api/containers")
async def list_containers(cm: ContainerManager = Depends(get_container_manager)):
    """List running containers"""
    try:
        return {
            "status": "success",
            "containers": cm.list_experiments()
        }
    except Exception as e:
        logger.error(f"Failed to list containers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/containers/{experiment_id}/logs")
async def get_container_logs(
    experiment_id: str,
    tail: int = 100,
    cm: ContainerManager = Depends(get_container_manager)
):
    """Get container logs"""
    try:
        logs = cm.get_experiment_logs(experiment_id, tail)
        if logs is None:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {"status": "success", "logs": logs}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get container logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/containers/{experiment_id}/stop")
async def stop_container(
    experiment_id: str,
    cm: ContainerManager = Depends(get_container_manager)
):
    """Stop container"""
    try:
        success = cm.stop_experiment(experiment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Experiment not found")
        return {"status": "success", "message": "Container stopped"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop container: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Maintenance endpoints
@app.post("/api/maintenance/cleanup")
async def cleanup_old_experiments(
    max_age_hours: int = 24,
    cm: ContainerManager = Depends(get_container_manager)
):
    """Clean up old experiments"""
    try:
        cleaned_count = cm.cleanup_old_experiments(max_age_hours)
        return {
            "status": "success",
            "cleaned_count": cleaned_count,
            "message": f"Cleaned up {cleaned_count} old experiments"
        }
    except Exception as e:
        logger.error(f"Failed to cleanup old experiments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
