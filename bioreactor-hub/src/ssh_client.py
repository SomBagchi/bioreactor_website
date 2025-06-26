"""
SSH Client for Bioreactor Hub
Handles SSH communication with bioreactor-node for experiment forwarding.
"""

import os
import logging
import json
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
            if not self.key_path or not Path(self.key_path).exists():
                raise ValueError("SSH key not found. Please set SSH_KEY_PATH to a valid private key file")
                
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                key_filename=self.key_path
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
    
    def forward_experiment(self, experiment_id: str, script_content: str) -> Dict[str, Any]:
        """Forward experiment script to bioreactor-node"""
        # Create the script file on the node
        script_filename = f"/tmp/experiment_{experiment_id}.py"
        command = f'echo \'{script_content}\' > {script_filename}'
        result = self.execute_command(command)
        
        if not result["success"]:
            return {"success": False, "error": f"Failed to create script file: {result.get('error')}"}
        
        # Start the experiment container
        docker_command = f'docker run --rm -v {script_filename}:/app/user_script.py -e EXPERIMENT_ID={experiment_id} bioreactor-user-experiment'
        result = self.execute_command(docker_command)
        
        return result
    
    def get_experiment_status(self, experiment_id: str) -> Dict[str, Any]:
        """Get experiment status from bioreactor-node"""
        command = f"curl -s http://localhost:9000/api/experiments/{experiment_id}"
        result = self.execute_command(command)
        
        if result["success"]:
            try:
                return json.loads(result["stdout"])
            except json.JSONDecodeError:
                return {"error": "Invalid JSON response"}
        else:
            return {"error": result.get("error", "Unknown error")}
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
