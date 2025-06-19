"""
Container Manager for Bioreactor Hub
Manages user experiment containers with security and isolation.
"""

import os
import uuid
import logging
import asyncio
import tempfile
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import docker
from docker.errors import DockerException, ContainerError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ContainerConfig(BaseModel):
    """Configuration for user experiment containers"""
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    max_duration: int = 86400  # 24 hours in seconds
    allowed_packages: List[str] = ["numpy", "pandas", "matplotlib", "scikit-learn"]
    network_mode: str = "bridge"
    read_only: bool = True

class ExperimentContainer:
    """Represents a user experiment container"""
    
    def __init__(self, experiment_id: str, script_content: str, config: ContainerConfig):
        self.experiment_id = experiment_id
        self.script_content = script_content
        self.config = config
        self.container = None
        self.start_time = None
        self.end_time = None
        self.exit_code = None
        self.status = "created"
        self.output_dir = None
        
    def __str__(self):
        return f"ExperimentContainer(id={self.experiment_id}, status={self.status})"

class ContainerManager:
    """Manages user experiment containers"""
    
    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise
        
        # Container registry
        self.containers: Dict[str, ExperimentContainer] = {}
        
        # Default configuration
        self.default_config = ContainerConfig()
        
    def create_experiment_container(self, script_content: str, config: Optional[ContainerConfig] = None) -> str:
        """Create a new experiment container"""
        if config is None:
            config = self.default_config
            
        experiment_id = str(uuid.uuid4())
        
        # Create container instance
        container = ExperimentContainer(experiment_id, script_content, config)
        
        # Create output directory
        output_dir = self.data_dir / "experiments" / experiment_id
        output_dir.mkdir(parents=True, exist_ok=True)
        container.output_dir = output_dir
        
        # Store container reference
        self.containers[experiment_id] = container
        
        logger.info(f"Created experiment container: {experiment_id}")
        return experiment_id
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment container"""
        if experiment_id not in self.containers:
            logger.error(f"Experiment {experiment_id} not found")
            return False
            
        container = self.containers[experiment_id]
        
        try:
            # Create temporary script file
            script_file = container.output_dir / "user_script.py"
            with open(script_file, 'w') as f:
                f.write(container.script_content)
            
            # Create container
            container.container = self.docker_client.containers.run(
                image="bioreactor-user-experiment:latest",
                command=["python", "/workspace/user_script.py"],
                volumes={
                    str(container.output_dir / "output"): {
                        'bind': '/workspace/output',
                        'mode': 'rw'
                    },
                    str(script_file): {
                        'bind': '/workspace/user_script.py',
                        'mode': 'ro'
                    }
                },
                environment={
                    "BIOREACTOR_HUB_API_URL": "http://host.docker.internal:8000",
                    "EXPERIMENT_ID": experiment_id
                },
                detach=True,
                mem_limit=container.config.memory_limit,
                cpu_period=100000,
                cpu_quota=int(container.config.cpu_limit * 100000),
                network_mode=container.config.network_mode,
                read_only=container.config.read_only,
                name=f"experiment-{experiment_id}",
                remove=True
            )
            
            container.start_time = datetime.now()
            container.status = "running"
            
            logger.info(f"Started experiment container: {experiment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start experiment {experiment_id}: {e}")
            container.status = "failed"
            container.end_time = datetime.now()
            return False
    
    def stop_experiment(self, experiment_id: str) -> bool:
        """Stop an experiment container"""
        if experiment_id not in self.containers:
            logger.error(f"Experiment {experiment_id} not found")
            return False
            
        container = self.containers[experiment_id]
        
        if container.container is None:
            logger.warning(f"Experiment {experiment_id} has no running container")
            return True
            
        try:
            container.container.stop(timeout=30)
            container.status = "stopped"
            container.end_time = datetime.now()
            
            logger.info(f"Stopped experiment container: {experiment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop experiment {experiment_id}: {e}")
            return False
    
    def get_experiment_status(self, experiment_id: str) -> Optional[Dict]:
        """Get experiment status"""
        if experiment_id not in self.containers:
            return None
            
        container = self.containers[experiment_id]
        
        # Check if container is still running
        if container.container:
            try:
                container.reload()
                if container.status == "running":
                    # Check if container has exited
                    container_info = self.docker_client.api.inspect_container(container.id)
                    if container_info['State']['Status'] == 'exited':
                        container.status = "completed"
                        container.end_time = datetime.now()
                        container.exit_code = container_info['State']['ExitCode']
            except Exception as e:
                logger.error(f"Error checking container status: {e}")
        
        return {
            "experiment_id": experiment_id,
            "status": container.status,
            "start_time": container.start_time.isoformat() if container.start_time else None,
            "end_time": container.end_time.isoformat() if container.end_time else None,
            "exit_code": container.exit_code,
            "duration": self._calculate_duration(container.start_time, container.end_time)
        }
    
    def get_experiment_logs(self, experiment_id: str, tail: int = 100) -> Optional[str]:
        """Get experiment logs"""
        if experiment_id not in self.containers:
            return None
            
        container = self.containers[experiment_id]
        
        if container.container is None:
            return "No container logs available"
            
        try:
            logs = container.container.logs(tail=tail, timestamps=True)
            return logs.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to get logs for experiment {experiment_id}: {e}")
            return f"Error retrieving logs: {e}"
    
    def get_experiment_results(self, experiment_id: str) -> Optional[Dict]:
        """Get experiment results"""
        if experiment_id not in self.containers:
            return None
            
        container = self.containers[experiment_id]
        
        if container.output_dir is None:
            return None
            
        results = {
            "experiment_id": experiment_id,
            "output_files": [],
            "stdout": None,
            "stderr": None,
            "exit_code": container.exit_code
        }
        
        # Check for output files
        output_dir = container.output_dir / "output"
        if output_dir.exists():
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    results["output_files"].append(str(file_path.relative_to(output_dir)))
        
        # Check for stdout/stderr files
        stdout_file = container.output_dir / "stdout.txt"
        stderr_file = container.output_dir / "stderr.txt"
        
        if stdout_file.exists():
            with open(stdout_file, 'r') as f:
                results["stdout"] = f.read()
                
        if stderr_file.exists():
            with open(stderr_file, 'r') as f:
                results["stderr"] = f.read()
        
        return results
    
    def create_results_zip(self, experiment_id: str) -> Optional[Path]:
        """Create a ZIP file with experiment results"""
        if experiment_id not in self.containers:
            return None
            
        container = self.containers[experiment_id]
        
        if container.output_dir is None:
            return None
            
        zip_path = container.output_dir / "results.zip"
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add output files
                output_dir = container.output_dir / "output"
                if output_dir.exists():
                    for file_path in output_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = f"output/{file_path.relative_to(output_dir)}"
                            zipf.write(file_path, arcname)
                
                # Add stdout/stderr
                stdout_file = container.output_dir / "stdout.txt"
                stderr_file = container.output_dir / "stderr.txt"
                
                if stdout_file.exists():
                    zipf.write(stdout_file, "stdout.txt")
                if stderr_file.exists():
                    zipf.write(stderr_file, "stderr.txt")
                
                # Add exit code
                exit_code_file = container.output_dir / "exitcode.txt"
                with open(exit_code_file, 'w') as f:
                    f.write(str(container.exit_code or 0))
                zipf.write(exit_code_file, "exitcode.txt")
            
            return zip_path
            
        except Exception as e:
            logger.error(f"Failed to create results ZIP for experiment {experiment_id}: {e}")
            return None
    
    def cleanup_experiment(self, experiment_id: str) -> bool:
        """Clean up experiment resources"""
        if experiment_id not in self.containers:
            return False
            
        container = self.containers[experiment_id]
        
        # Stop container if running
        if container.container:
            try:
                container.container.stop(timeout=10)
            except Exception as e:
                logger.warning(f"Error stopping container during cleanup: {e}")
        
        # Remove from registry
        del self.containers[experiment_id]
        
        logger.info(f"Cleaned up experiment: {experiment_id}")
        return True
    
    def list_experiments(self) -> List[Dict]:
        """List all experiments"""
        return [
            self.get_experiment_status(exp_id)
            for exp_id in self.containers.keys()
        ]
    
    def cleanup_old_experiments(self, max_age_hours: int = 24) -> int:
        """Clean up experiments older than specified age"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        for experiment_id, container in list(self.containers.items()):
            if container.end_time and container.end_time < cutoff_time:
                if self.cleanup_experiment(experiment_id):
                    cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old experiments")
        return cleaned_count
    
    def _calculate_duration(self, start_time: Optional[datetime], end_time: Optional[datetime]) -> Optional[float]:
        """Calculate experiment duration in seconds"""
        if start_time is None:
            return None
            
        if end_time is None:
            end_time = datetime.now()
            
        return (end_time - start_time).total_seconds() 
