"""
Bioreactor Node - Hardware Interface API
Provides REST API access to bioreactor hardware functionality.
"""

import os
import logging
import uuid
import zipfile
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import docker

from .bioreactor import Bioreactor
from .config import Config as cfg

# Configure logging
logging.basicConfig(
    level=getattr(logging, cfg.LOG_LEVEL),
    format=cfg.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Global instances
bioreactor: Optional[Bioreactor] = None
docker_client: Optional[docker.DockerClient] = None
containers: Dict[str, Dict] = {}

class HardwareMode:
    """Hardware mode configuration"""
    SIMULATION = "simulation"
    REAL = "real"

# Pydantic models for API requests/responses
class LEDRequest(BaseModel):
    state: bool

class RingLightRequest(BaseModel):
    color: List[int]  # RGB values [r, g, b]
    pixel: Optional[int] = None

class PeltierRequest(BaseModel):
    power: int  # 0-100
    forward: bool

class PumpRequest(BaseModel):
    pump_name: str
    ml_per_sec: float

class StirrerRequest(BaseModel):
    duty_cycle: int  # 0-100

class ExperimentRequest(BaseModel):
    script_content: str
    experiment_id: Optional[str] = None

class ExperimentStatus(BaseModel):
    experiment_id: str
    status: str  # running, completed, failed, stopped
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global bioreactor, docker_client
    
    # Startup
    logger.info("Starting Bioreactor Node API...")
    
    # Initialize Docker client
    try:
        docker_client = docker.from_env()
        logger.info("Docker client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Docker client: {e}")
        docker_client = None
    
    # Initialize bioreactor based on hardware mode
    hardware_mode = os.getenv("HARDWARE_MODE", HardwareMode.SIMULATION)
    logger.info(f"Hardware mode: {hardware_mode}")
    
    if hardware_mode == HardwareMode.REAL:
        try:
            bioreactor = Bioreactor()
            logger.info("Bioreactor hardware initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bioreactor hardware: {e}")
            bioreactor = None
    else:
        logger.info("Running in simulation mode - no hardware access")
        bioreactor = None
    
    yield
    
    # Shutdown
    logger.info("Shutting down Bioreactor Node API...")
    
    # Stop all running containers
    if docker_client:
        for experiment_id, container_info in containers.items():
            if container_info.get("container"):
                try:
                    container_info["container"].stop(timeout=10)
                    logger.info(f"Stopped container for experiment {experiment_id}")
                except Exception as e:
                    logger.error(f"Failed to stop container for experiment {experiment_id}: {e}")
    
    if bioreactor:
        try:
            bioreactor.finish()
            logger.info("Bioreactor hardware shutdown complete")
        except Exception as e:
            logger.error(f"Error during bioreactor shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="Bioreactor Node API",
    description="REST API for bioreactor hardware control and experiment management",
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

def get_bioreactor() -> Bioreactor:
    """Get bioreactor instance or raise error"""
    if bioreactor is None:
        raise HTTPException(
            status_code=503,
            detail="Bioreactor hardware not available"
        )
    return bioreactor

def get_docker_client() -> docker.DockerClient:
    """Get Docker client or raise error"""
    if docker_client is None:
        raise HTTPException(
            status_code=503,
            detail="Docker client not available"
        )
    return docker_client

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "hardware_available": bioreactor is not None,
        "hardware_mode": os.getenv("HARDWARE_MODE", HardwareMode.SIMULATION),
        "docker_available": docker_client is not None,
        "running_experiments": len([c for c in containers.values() if c.get("status") == "running"])
    }

# Hardware status endpoint
@app.get("/api/status")
async def get_status():
    """Get overall hardware status"""
    if bioreactor is None:
        return {
            "status": "simulation_mode",
            "hardware_available": False,
            "initialized_components": {}
        }
    
    return {
        "status": "operational",
        "hardware_available": True,
        "initialized_components": bioreactor._initialized
    }

# LED control endpoint
@app.post("/api/led")
async def control_led(request: LEDRequest):
    """Control LED state"""
    bio = get_bioreactor()
    try:
        bio.change_led(request.state)
        return {"status": "success", "led_state": request.state}
    except Exception as e:
        logger.error(f"LED control error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Ring light control endpoint
@app.post("/api/ring-light")
async def control_ring_light(request: RingLightRequest):
    """Control ring light"""
    bio = get_bioreactor()
    try:
        bio.change_ring_light(request.color, request.pixel)
        return {"status": "success", "color": request.color}
    except Exception as e:
        logger.error(f"Ring light control error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Peltier control endpoint
@app.post("/api/peltier")
async def control_peltier(request: PeltierRequest):
    """Control peltier (temperature control)"""
    bio = get_bioreactor()
    try:
        bio.change_peltier(request.power, request.forward)
        return {
            "status": "success",
            "power": request.power,
            "forward": request.forward
        }
    except Exception as e:
        logger.error(f"Peltier control error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Pump control endpoint
@app.post("/api/pump")
async def control_pump(request: PumpRequest):
    """Control pump flow rate"""
    bio = get_bioreactor()
    try:
        bio.change_pump(request.pump_name, request.ml_per_sec)
        return {
            "status": "success",
            "pump": request.pump_name,
            "flow_rate_ml_s": request.ml_per_sec
        }
    except Exception as e:
        logger.error(f"Pump control error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Stirrer control endpoint
@app.post("/api/stirrer")
async def control_stirrer(request: StirrerRequest):
    """Control stirrer speed"""
    bio = get_bioreactor()
    try:
        bio.stirrer.ChangeDutyCycle(request.duty_cycle)
        return {
            "status": "success",
            "duty_cycle": request.duty_cycle
        }
    except Exception as e:
        logger.error(f"Stirrer control error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Sensor data endpoints
@app.get("/api/sensors/photodiodes")
async def get_photodiodes():
    """Get photodiode readings"""
    bio = get_bioreactor()
    try:
        readings = bio.get_photodiodes()
        return {
            "status": "success",
            "readings": readings,
            "labels": [cfg.SENSOR_LABELS[f'photodiode_{i+1}'] for i in range(len(readings))]
        }
    except Exception as e:
        logger.error(f"Photodiode reading error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sensors/temperature")
async def get_temperature():
    """Get temperature readings"""
    bio = get_bioreactor()
    try:
        vial_temps = bio.get_vial_temp()
        io_temps = bio.get_io_temp()
        return {
            "status": "success",
            "vial_temperatures": vial_temps,
            "io_temperatures": io_temps,
            "vial_labels": [cfg.SENSOR_LABELS[f'vial_temp_{i+1}'] for i in range(len(vial_temps))],
            "io_labels": [cfg.SENSOR_LABELS[f'io_temp_{i+1}'] for i in range(len(io_temps))]
        }
    except Exception as e:
        logger.error(f"Temperature reading error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sensors/current")
async def get_current():
    """Get current readings"""
    bio = get_bioreactor()
    try:
        current = bio.get_peltier_curr()
        return {
            "status": "success",
            "peltier_current": current,
            "label": cfg.SENSOR_LABELS['peltier_current']
        }
    except Exception as e:
        logger.error(f"Current reading error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sensors/all")
async def get_all_sensors():
    """Get all sensor readings"""
    bio = get_bioreactor()
    try:
        photodiodes = bio.get_photodiodes()
        vial_temps = bio.get_vial_temp()
        io_temps = bio.get_io_temp()
        current = bio.get_peltier_curr()
        
        return {
            "status": "success",
            "photodiodes": photodiodes,
            "vial_temperatures": vial_temps,
            "io_temperatures": io_temps,
            "peltier_current": current,
            "timestamp": bio.writer.writerow.__self__.out_file.tell() if hasattr(bio, 'writer') else None
        }
    except Exception as e:
        logger.error(f"All sensors reading error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Experiment management endpoints
@app.post("/api/experiments/start")
async def start_experiment(request: ExperimentRequest, background_tasks: BackgroundTasks):
    """Start a new experiment"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker not available")
    
    # Generate experiment ID if not provided
    experiment_id = request.experiment_id or str(uuid.uuid4())
    
    # Create experiment directory
    data_dir = Path("/app/data")
    experiment_dir = data_dir / "experiments" / experiment_id
    experiment_dir.mkdir(parents=True, exist_ok=True)
    
    # Save user script
    script_file = experiment_dir / "user_script.py"
    with open(script_file, 'w') as f:
        f.write(request.script_content)
    
    # Create output directory
    output_dir = experiment_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Start container in background
        background_tasks.add_task(run_experiment_container, experiment_id, script_file, output_dir)
        
        # Store experiment info
        containers[experiment_id] = {
            "status": "starting",
            "start_time": datetime.now(),
            "script_file": str(script_file),
            "output_dir": str(output_dir),
            "container": None
        }
        
        logger.info(f"Started experiment: {experiment_id}")
        return {
            "status": "success",
            "experiment_id": experiment_id,
            "message": "Experiment started"
        }
        
    except Exception as e:
        logger.error(f"Failed to start experiment {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_experiment_container(experiment_id: str, script_file: Path, output_dir: Path):
    """Run experiment in Docker container"""
    try:
        # Update status
        containers[experiment_id]["status"] = "running"
        
        # Run container
        container = docker_client.containers.run(
            image="bioreactor-user-experiment:latest",
            command=["python", "/app/user_script.py"],
            volumes={
                str(output_dir): {
                    'bind': '/app/output',
                    'mode': 'rw'
                },
                str(script_file): {
                    'bind': '/app/user_script.py',
                    'mode': 'ro'
                }
            },
            environment={
                "BIOREACTOR_NODE_API_URL": "http://host.docker.internal:9000",
                "EXPERIMENT_ID": experiment_id
            },
            detach=True,
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=100000,  # 1 CPU core
            network_mode="host",  # Use host network for direct access
            name=f"experiment-{experiment_id}",
            remove=True
        )
        
        # Store container reference
        containers[experiment_id]["container"] = container
        
        # Wait for container to complete
        result = container.wait()
        
        # Update status
        containers[experiment_id]["status"] = "completed" if result["StatusCode"] == 0 else "failed"
        containers[experiment_id]["end_time"] = datetime.now()
        containers[experiment_id]["exit_code"] = result["StatusCode"]
        
        logger.info(f"Experiment {experiment_id} completed with exit code {result['StatusCode']}")
        
    except Exception as e:
        logger.error(f"Error running experiment {experiment_id}: {e}")
        containers[experiment_id]["status"] = "failed"
        containers[experiment_id]["end_time"] = datetime.now()
        containers[experiment_id]["error_message"] = str(e)

@app.get("/api/experiments/{experiment_id}/status")
async def get_experiment_status(experiment_id: str):
    """Get experiment status"""
    if experiment_id not in containers:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    container_info = containers[experiment_id]
    
    # Check if container is still running
    if container_info.get("container"):
        try:
            container_info["container"].reload()
            if container_info["status"] == "running":
                # Check if container has exited
                container_data = docker_client.api.inspect_container(container_info["container"].id)
                if container_data['State']['Status'] == 'exited':
                    container_info["status"] = "completed"
                    container_info["end_time"] = datetime.now()
                    container_info["exit_code"] = container_data['State']['ExitCode']
        except Exception as e:
            logger.error(f"Error checking container status: {e}")
    
    return {
        "status": "success",
        "experiment": {
            "experiment_id": experiment_id,
            "status": container_info["status"],
            "start_time": container_info["start_time"].isoformat() if container_info.get("start_time") else None,
            "end_time": container_info["end_time"].isoformat() if container_info.get("end_time") else None,
            "exit_code": container_info.get("exit_code"),
            "error_message": container_info.get("error_message")
        }
    }

@app.get("/api/experiments/{experiment_id}/logs")
async def get_experiment_logs(experiment_id: str, tail: int = 100):
    """Get experiment logs"""
    if experiment_id not in containers:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    container_info = containers[experiment_id]
    container = container_info.get("container")
    
    if container is None:
        return {"status": "success", "logs": "No container logs available"}
    
    try:
        logs = container.logs(tail=tail, timestamps=True)
        return {"status": "success", "logs": logs.decode('utf-8')}
    except Exception as e:
        logger.error(f"Failed to get logs for experiment {experiment_id}: {e}")
        return {"status": "error", "logs": f"Error retrieving logs: {e}"}

@app.get("/api/experiments/{experiment_id}/results")
async def get_experiment_results(experiment_id: str):
    """Get experiment results"""
    if experiment_id not in containers:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    container_info = containers[experiment_id]
    output_dir = Path(container_info["output_dir"])
    
    results = {
        "experiment_id": experiment_id,
        "output_files": [],
        "exit_code": container_info.get("exit_code")
    }
    
    # Check for output files
    if output_dir.exists():
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                results["output_files"].append(str(file_path.relative_to(output_dir)))
    
    return {"status": "success", "results": results}

@app.get("/api/experiments/{experiment_id}/download")
async def download_experiment_results(experiment_id: str):
    """Download experiment results as ZIP file"""
    if experiment_id not in containers:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    container_info = containers[experiment_id]
    output_dir = Path(container_info["output_dir"])
    zip_path = output_dir.parent / "results.zip"
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add output files
            if output_dir.exists():
                for file_path in output_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(output_dir)
                        zipf.write(file_path, arcname)
            
            # Add script file
            script_file = Path(container_info["script_file"])
            if script_file.exists():
                zipf.write(script_file, "user_script.py")
        
        return FileResponse(
            path=str(zip_path),
            filename=f"experiment_{experiment_id}_results.zip",
            media_type="application/zip"
        )
    except Exception as e:
        logger.error(f"Failed to create results ZIP for experiment {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/experiments/{experiment_id}/stop")
async def stop_experiment(experiment_id: str):
    """Stop experiment"""
    if experiment_id not in containers:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    container_info = containers[experiment_id]
    container = container_info.get("container")
    
    if container is None:
        return {"status": "success", "message": "No running container to stop"}
    
    try:
        container.stop(timeout=30)
        container_info["status"] = "stopped"
        container_info["end_time"] = datetime.now()
        
        logger.info(f"Stopped experiment: {experiment_id}")
        return {"status": "success", "message": "Experiment stopped"}
    except Exception as e:
        logger.error(f"Failed to stop experiment {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/experiments/{experiment_id}")
async def delete_experiment(experiment_id: str):
    """Delete experiment"""
    if experiment_id not in containers:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    container_info = containers[experiment_id]
    
    # Stop container if running
    container = container_info.get("container")
    if container:
        try:
            container.stop(timeout=10)
        except Exception as e:
            logger.error(f"Failed to stop container for experiment {experiment_id}: {e}")
    
    # Remove experiment data
    try:
        import shutil
        experiment_dir = Path(container_info["output_dir"]).parent
        if experiment_dir.exists():
            shutil.rmtree(experiment_dir)
    except Exception as e:
        logger.error(f"Failed to remove experiment directory for {experiment_id}: {e}")
    
    # Remove from containers dict
    del containers[experiment_id]
    
    logger.info(f"Deleted experiment: {experiment_id}")
    return {"status": "success", "message": "Experiment deleted"}

@app.get("/api/experiments")
async def list_experiments():
    """List all experiments"""
    experiment_list = []
    for experiment_id, container_info in containers.items():
        experiment_list.append({
            "experiment_id": experiment_id,
            "status": container_info["status"],
            "start_time": container_info["start_time"].isoformat() if container_info.get("start_time") else None,
            "end_time": container_info["end_time"].isoformat() if container_info.get("end_time") else None
        })
    
    return {"status": "success", "experiments": experiment_list}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,
        log_level="info"
    ) 
