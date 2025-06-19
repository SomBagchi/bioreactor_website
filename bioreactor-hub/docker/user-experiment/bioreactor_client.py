"""
Bioreactor Client Library for User Experiments
Provides a safe interface to bioreactor hardware through the hub API.
"""

import os
import time
import logging
import requests
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BioreactorClient:
    """Client for communicating with bioreactor hardware through hub API"""
    
    def __init__(self, api_url: Optional[str] = None):
        """Initialize bioreactor client"""
        self.api_url = api_url or os.getenv("BIOREACTOR_HUB_API_URL", "http://host.docker.internal:8000")
        self.session = requests.Session()
        self.session.timeout = 30
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to hub API"""
        url = f"{self.api_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise ConnectionError(f"Failed to communicate with bioreactor hub: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get hardware status"""
        return self._make_request("GET", "/api/hardware/status")
    
    def get_sensors(self) -> Dict[str, Any]:
        """Get all sensor data"""
        return self._make_request("GET", "/api/hardware/sensors")
    
    def get_photodiodes(self) -> Dict[str, Any]:
        """Get photodiode readings"""
        return self._make_request("GET", "/api/hardware/sensors/photodiodes")
    
    def get_temperature(self) -> Dict[str, Any]:
        """Get temperature readings"""
        return self._make_request("GET", "/api/hardware/sensors/temperature")
    
    def get_current(self) -> Dict[str, Any]:
        """Get current readings"""
        return self._make_request("GET", "/api/hardware/sensors/current")
    
    def control_led(self, state: bool) -> Dict[str, Any]:
        """Control LED"""
        return self._make_request("POST", "/api/hardware/led", {"state": state})
    
    def control_ring_light(self, color: List[int], pixel: Optional[int] = None) -> Dict[str, Any]:
        """Control ring light"""
        data = {"color": color}
        if pixel is not None:
            data["pixel"] = pixel
        return self._make_request("POST", "/api/hardware/ring-light", data)
    
    def control_peltier(self, power: int, forward: bool) -> Dict[str, Any]:
        """Control peltier (temperature control)"""
        return self._make_request("POST", "/api/hardware/peltier", {
            "power": power,
            "forward": forward
        })
    
    def control_pump(self, pump_name: str, ml_per_sec: float) -> Dict[str, Any]:
        """Control pump flow rate"""
        return self._make_request("POST", "/api/hardware/pump", {
            "pump_name": pump_name,
            "ml_per_sec": ml_per_sec
        })
    
    def control_stirrer(self, duty_cycle: int) -> Dict[str, Any]:
        """Control stirrer speed"""
        return self._make_request("POST", "/api/hardware/stirrer", {
            "duty_cycle": duty_cycle
        })

class Bioreactor:
    """Bioreactor class that mimics the original Bioreactor interface"""
    
    def __init__(self):
        """Initialize bioreactor interface"""
        self.client = BioreactorClient()
        self.logger = logger
        self._temp_integral = 0.0
        self._temp_last_error = 0.0
        
        # Test connection
        try:
            status = self.client.get_status()
            logger.info("Bioreactor interface initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bioreactor interface: {e}")
            raise
    
    def change_led(self, state: bool) -> None:
        """Change LED state"""
        result = self.client.control_led(state)
        if result.get("status") != "success":
            raise RuntimeError(f"LED control failed: {result}")
    
    def change_ring_light(self, color: List[int], pixel: Optional[int] = None) -> None:
        """Change ring light color"""
        result = self.client.control_ring_light(color, pixel)
        if result.get("status") != "success":
            raise RuntimeError(f"Ring light control failed: {result}")
    
    def change_peltier(self, power: int, forward: bool) -> None:
        """Change peltier power and direction"""
        result = self.client.control_peltier(power, forward)
        if result.get("status") != "success":
            raise RuntimeError(f"Peltier control failed: {result}")
    
    def change_pump(self, pump_name: str, ml_per_sec: float) -> None:
        """Change pump flow rate"""
        result = self.client.control_pump(pump_name, ml_per_sec)
        if result.get("status") != "success":
            raise RuntimeError(f"Pump control failed: {result}")
    
    def get_photodiodes(self) -> List[float]:
        """Get photodiode readings"""
        result = self.client.get_photodiodes()
        if result.get("status") == "success":
            return result.get("readings", [])
        else:
            raise RuntimeError(f"Failed to get photodiode readings: {result}")
    
    def get_vial_temp(self) -> List[float]:
        """Get vial temperature readings"""
        result = self.client.get_temperature()
        if result.get("status") == "success":
            return result.get("vial_temperatures", [])
        else:
            raise RuntimeError(f"Failed to get temperature readings: {result}")
    
    def get_io_temp(self) -> List[float]:
        """Get IO temperature readings"""
        result = self.client.get_temperature()
        if result.get("status") == "success":
            return result.get("io_temperatures", [])
        else:
            raise RuntimeError(f"Failed to get temperature readings: {result}")
    
    def get_peltier_curr(self) -> float:
        """Get peltier current reading"""
        result = self.client.get_current()
        if result.get("status") == "success":
            return result.get("peltier_current", 0.0)
        else:
            raise RuntimeError(f"Failed to get current reading: {result}")
    
    def run(self, jobs: List) -> None:
        """Run jobs (placeholder for compatibility)"""
        logger.info("Bioreactor.run() called - this is a placeholder for compatibility")
        # In the containerized environment, jobs are handled differently
        # This maintains compatibility with existing scripts
    
    def stop_all(self) -> None:
        """Stop all operations (placeholder for compatibility)"""
        logger.info("Bioreactor.stop_all() called - this is a placeholder for compatibility")
    
    def finish(self) -> None:
        """Finish bioreactor operations (placeholder for compatibility)"""
        logger.info("Bioreactor.finish() called - this is a placeholder for compatibility")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit"""
        self.finish()

# Utility functions that mimic the original utils.py
def measure_and_write_sensor_data(bioreactor: Bioreactor, elapsed: float) -> Dict[str, Any]:
    """Get sensor measurements and return as dictionary"""
    photodiodes = bioreactor.get_photodiodes()
    io_temps = bioreactor.get_io_temp()
    vial_temps = bioreactor.get_vial_temp()
    peltier_current = bioreactor.get_peltier_curr()
    
    data_row = {
        'time': elapsed,
        'photodiodes': photodiodes,
        'io_temperatures': io_temps,
        'vial_temperatures': vial_temps,
        'peltier_current': peltier_current
    }
    
    bioreactor.logger.info(f"Measured sensor data: {data_row}")
    return data_row

def pid_controller(bioreactor: Bioreactor, setpoint: float, current_temp: Optional[float] = None, 
                  kp: float = 10.0, ki: float = 1.0, kd: float = 0.0, dt: float = 1.0, elapsed: Optional[float] = None):
    """PID loop to maintain reactor temperature at setpoint"""
    if current_temp is None:
        temps = bioreactor.get_vial_temp()
        current_temp = temps[0] if temps else 0.0
    
    error = setpoint - current_temp
    bioreactor._temp_integral += error * dt
    derivative = (error - bioreactor._temp_last_error) / dt if dt > 0 else 0.0
    output = kp * error + ki * bioreactor._temp_integral + kd * derivative
    
    duty = max(0, min(100, int(abs(output))))
    forward = (output >= 0)
    bioreactor.change_peltier(duty, forward)
    bioreactor._temp_last_error = error
    
    bioreactor.logger.info(f"PID controller: setpoint={setpoint}, current_temp={current_temp}, output={output}, duty={duty}, forward={forward}")

def balanced_flow(bioreactor: Bioreactor, pump_name: str, ml_per_sec: float, elapsed: Optional[float] = None):
    """For a given pump, set its flow and automatically set the converse pump to the same rate"""
    if pump_name.endswith('_in'):
        converse = pump_name[:-3] + 'out'
    elif pump_name.endswith('_out'):
        converse = pump_name[:-4] + 'in'
    else:
        raise ValueError("Pump name must end with '_in' or '_out'")
    
    bioreactor.change_pump(pump_name, ml_per_sec)
    bioreactor.change_pump(converse, ml_per_sec)
    
    bioreactor.logger.info(f"Balanced flow: {pump_name} and {converse} set to {ml_per_sec} ml/sec") 
