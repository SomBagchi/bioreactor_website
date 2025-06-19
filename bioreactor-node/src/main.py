"""
Bioreactor Node - Hardware Interface API
Provides REST API access to bioreactor hardware functionality.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .bioreactor import Bioreactor
from .config import Config as cfg

# Configure logging
logging.basicConfig(
    level=getattr(logging, cfg.LOG_LEVEL),
    format=cfg.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Global bioreactor instance
bioreactor: Optional[Bioreactor] = None

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
    experiment_id: str
    script_content: str

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
    global bioreactor
    
    # Startup
    logger.info("Starting Bioreactor Node API...")
    
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
    if bioreactor:
        try:
            bioreactor.finish()
            logger.info("Bioreactor hardware shutdown complete")
        except Exception as e:
            logger.error(f"Error during bioreactor shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="Bioreactor Node API",
    description="REST API for bioreactor hardware control",
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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "hardware_available": bioreactor is not None,
        "hardware_mode": os.getenv("HARDWARE_MODE", HardwareMode.SIMULATION)
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
@app.post("/api/experiment/start")
async def start_experiment(request: ExperimentRequest):
    """Start a new experiment"""
    # This is a placeholder - actual experiment management will be handled by bioreactor-hub
    return {
        "status": "success",
        "experiment_id": request.experiment_id,
        "message": "Experiment start request received"
    }

@app.get("/api/experiment/status")
async def get_experiment_status():
    """Get current experiment status"""
    return {
        "status": "no_experiment_running",
        "message": "No experiment currently running on this node"
    }

@app.post("/api/experiment/stop")
async def stop_experiment():
    """Stop current experiment"""
    return {
        "status": "success",
        "message": "No experiment to stop"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,
        log_level="info"
    ) 
