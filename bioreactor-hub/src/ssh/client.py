"""
SSH Client for Bioreactor Hub
Handles SSH communication with bioreactor-node.
"""

import os
import logging
import json
import asyncio
from typing import Dict, Optional, Any
from pathlib import Path

import paramiko
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import SSHException, AuthenticationException

logger = logging.getLogger(__name__)

class BioreactorNodeClient:
    """SSH client for communicating with bioreactor-node"""
    
    def __init__(self, host: str, port: int = 22, username: str = "pi", key_path: Optional[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.key_path = key_path
        self.client = None
        self.connected = False
        
    def connect(self) -> bool:
        """Establish SSH connection to bioreactor-node"""
        try:
            self.client = SSHClient()
            self.client.set_missing_host_key_policy(AutoAddPolicy())
            
            # Use key-based authentication if key path is provided
            if self.key_path and Path(self.key_path).exists():
                self.client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    key_filename=self.key_path
                )
            else:
                # Fall back to password authentication (not recommended for production)
                password = os.getenv("BIOREACTOR_NODE_PASSWORD")
                if not password:
                    raise ValueError("No SSH key or password provided")
                    
                self.client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=password
                )
            
            self.connected = True
            logger.info(f"SSH connection established to {self.host}:{self.port}")
            return True
            
        except (SSHException, AuthenticationException) as e:
            logger.error(f"SSH connection failed: {e}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error during SSH connection: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("SSH connection closed")
    
    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a command on bioreactor-node"""
        if not self.connected or not self.client:
            return {"success": False, "error": "Not connected"}
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            
            # Get output
            stdout_data = stdout.read().decode('utf-8').strip()
            stderr_data = stderr.read().decode('utf-8').strip()
            exit_code = stdout.channel.recv_exit_status()
            
            return {
                "success": exit_code == 0,
                "stdout": stdout_data,
                "stderr": stderr_data,
                "exit_code": exit_code
            }
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_hardware_status(self) -> Dict[str, Any]:
        """Get hardware status from bioreactor-node"""
        command = "curl -s http://localhost:9000/api/status"
        result = self.execute_command(command)
        
        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return {"error": "Invalid JSON response"}
        else:
            return {"error": result.get("error", "Unknown error")}
    
    def get_sensor_data(self) -> Dict[str, Any]:
        """Get sensor data from bioreactor-node"""
        command = "curl -s http://localhost:9000/api/sensors/all"
        result = self.execute_command(command)
        
        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return {"error": "Invalid JSON response"}
        else:
            return {"error": result.get("error", "Unknown error")}
    
    def control_hardware(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send hardware control command to bioreactor-node"""
        json_data = json.dumps(data)
        command = f'curl -s -X POST http://localhost:9000{endpoint} -H "Content-Type: application/json" -d \'{json_data}\''
        result = self.execute_command(command)
        
        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return {"error": "Invalid JSON response"}
        else:
            return {"error": result.get("error", "Unknown error")}
    
    def control_led(self, state: bool) -> Dict[str, Any]:
        """Control LED on bioreactor-node"""
        return self.control_hardware("/api/led", {"state": state})
    
    def control_ring_light(self, color: list, pixel: Optional[int] = None) -> Dict[str, Any]:
        """Control ring light on bioreactor-node"""
        data = {"color": color}
        if pixel is not None:
            data["pixel"] = pixel
        return self.control_hardware("/api/ring-light", data)
    
    def control_peltier(self, power: int, forward: bool) -> Dict[str, Any]:
        """Control peltier on bioreactor-node"""
        return self.control_hardware("/api/peltier", {"power": power, "forward": forward})
    
    def control_pump(self, pump_name: str, ml_per_sec: float) -> Dict[str, Any]:
        """Control pump on bioreactor-node"""
        return self.control_hardware("/api/pump", {"pump_name": pump_name, "ml_per_sec": ml_per_sec})
    
    def control_stirrer(self, duty_cycle: int) -> Dict[str, Any]:
        """Control stirrer on bioreactor-node"""
        return self.control_hardware("/api/stirrer", {"duty_cycle": duty_cycle})
    
    def get_photodiodes(self) -> Dict[str, Any]:
        """Get photodiode readings from bioreactor-node"""
        command = "curl -s http://localhost:9000/api/sensors/photodiodes"
        result = self.execute_command(command)
        
        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return {"error": "Invalid JSON response"}
        else:
            return {"error": result.get("error", "Unknown error")}
    
    def get_temperature(self) -> Dict[str, Any]:
        """Get temperature readings from bioreactor-node"""
        command = "curl -s http://localhost:9000/api/sensors/temperature"
        result = self.execute_command(command)
        
        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return {"error": "Invalid JSON response"}
        else:
            return {"error": result.get("error", "Unknown error")}
    
    def get_current(self) -> Dict[str, Any]:
        """Get current readings from bioreactor-node"""
        command = "curl -s http://localhost:9000/api/sensors/current"
        result = self.execute_command(command)
        
        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return {"error": "Invalid JSON response"}
        else:
            return {"error": result.get("error", "Unknown error")}
    
    def check_health(self) -> Dict[str, Any]:
        """Check health of bioreactor-node"""
        command = "curl -s http://localhost:9000/health"
        result = self.execute_command(command)
        
        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return {"error": "Invalid JSON response"}
        else:
            return {"error": result.get("error", "Unknown error")}
    
    def restart_service(self) -> Dict[str, Any]:
        """Restart bioreactor-node service"""
        command = "sudo systemctl restart bioreactor-node"
        return self.execute_command(command)
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get bioreactor-node service status"""
        command = "systemctl status bioreactor-node"
        return self.execute_command(command)
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

class AsyncBioreactorNodeClient:
    """Async wrapper for BioreactorNodeClient"""
    
    def __init__(self, host: str, port: int = 22, username: str = "pi", key_path: Optional[str] = None):
        self.client = BioreactorNodeClient(host, port, username, key_path)
    
    async def connect(self) -> bool:
        """Async connect"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.client.connect)
    
    async def disconnect(self):
        """Async disconnect"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.client.disconnect)
    
    async def get_hardware_status(self) -> Dict[str, Any]:
        """Async get hardware status"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.client.get_hardware_status)
    
    async def get_sensor_data(self) -> Dict[str, Any]:
        """Async get sensor data"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.client.get_sensor_data)
    
    async def control_hardware(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Async control hardware"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.client.control_hardware, endpoint, data)
    
    async def check_health(self) -> Dict[str, Any]:
        """Async health check"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.client.check_health) 
