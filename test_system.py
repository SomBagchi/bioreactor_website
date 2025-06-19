#!/usr/bin/env python3
"""
Test script for bioreactor system components
Tests the bioreactor-node and bioreactor-hub APIs
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# Configuration
BIOREACTOR_NODE_URL = "http://localhost:9000"
BIOREACTOR_HUB_URL = "http://localhost:8000"

def test_bioreactor_node():
    """Test bioreactor-node API"""
    print("🧪 Testing Bioreactor Node API...")
    
    # Test health check
    try:
        response = requests.get(f"{BIOREACTOR_NODE_URL}/health")
        if response.status_code == 200:
            print("✅ Bioreactor Node health check passed")
            print(f"   Status: {response.json()}")
        else:
            print(f"❌ Bioreactor Node health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bioreactor Node not accessible: {e}")
        return False
    
    # Test hardware status
    try:
        response = requests.get(f"{BIOREACTOR_NODE_URL}/api/status")
        if response.status_code == 200:
            print("✅ Bioreactor Node hardware status check passed")
            print(f"   Status: {response.json()}")
        else:
            print(f"❌ Bioreactor Node hardware status check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Bioreactor Node hardware status check failed: {e}")
    
    # Test sensor data (if hardware is available)
    try:
        response = requests.get(f"{BIOREACTOR_NODE_URL}/api/sensors/all")
        if response.status_code == 200:
            print("✅ Bioreactor Node sensor data check passed")
            data = response.json()
            print(f"   Photodiodes: {len(data.get('photodiodes', []))} readings")
            print(f"   Temperatures: {len(data.get('vial_temperatures', []))} readings")
        else:
            print(f"❌ Bioreactor Node sensor data check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Bioreactor Node sensor data check failed: {e}")
    
    return True

def test_bioreactor_hub():
    """Test bioreactor-hub API"""
    print("\n🧪 Testing Bioreactor Hub API...")
    
    # Test health check
    try:
        response = requests.get(f"{BIOREACTOR_HUB_URL}/health")
        if response.status_code == 200:
            print("✅ Bioreactor Hub health check passed")
            print(f"   Status: {response.json()}")
        else:
            print(f"❌ Bioreactor Hub health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bioreactor Hub not accessible: {e}")
        return False
    
    # Test hardware abstraction
    try:
        response = requests.get(f"{BIOREACTOR_HUB_URL}/api/hardware/status")
        if response.status_code == 200:
            print("✅ Bioreactor Hub hardware abstraction check passed")
            print(f"   Status: {response.json()}")
        else:
            print(f"❌ Bioreactor Hub hardware abstraction check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Bioreactor Hub hardware abstraction check failed: {e}")
    
    # Test experiment management
    try:
        response = requests.get(f"{BIOREACTOR_HUB_URL}/api/experiments")
        if response.status_code == 200:
            print("✅ Bioreactor Hub experiment management check passed")
            data = response.json()
            print(f"   Experiments: {len(data.get('experiments', []))} found")
        else:
            print(f"❌ Bioreactor Hub experiment management check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Bioreactor Hub experiment management check failed: {e}")
    
    return True

def test_experiment_workflow():
    """Test complete experiment workflow"""
    print("\n🧪 Testing Experiment Workflow...")
    
    # Create a simple test script
    test_script = '''
import time
import logging
from bioreactor_client import Bioreactor, measure_and_write_sensor_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        with Bioreactor() as bioreactor:
            logger.info("Starting test experiment...")
            
            # Get initial sensor data
            data = measure_and_write_sensor_data(bioreactor, 0.0)
            logger.info(f"Initial sensor data: {data}")
            
            # Control LED
            bioreactor.change_led(True)
            logger.info("LED turned on")
            
            # Wait a bit
            time.sleep(2)
            
            # Turn off LED
            bioreactor.change_led(False)
            logger.info("LED turned off")
            
            # Get final sensor data
            data = measure_and_write_sensor_data(bioreactor, 2.0)
            logger.info(f"Final sensor data: {data}")
            
            logger.info("Test experiment completed successfully")
            
    except Exception as e:
        logger.error(f"Test experiment failed: {e}")
        raise

if __name__ == "__main__":
    main()
'''
    
    # Start experiment
    try:
        response = requests.post(
            f"{BIOREACTOR_HUB_URL}/api/experiments/start",
            json={
                "script_content": test_script,
                "config": {
                    "memory_limit": "256m",
                    "cpu_limit": 0.5,
                    "max_duration": 300
                }
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            experiment_id = data.get("experiment_id")
            print(f"✅ Experiment started: {experiment_id}")
            
            # Wait for experiment to complete
            print("   Waiting for experiment to complete...")
            for i in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                
                status_response = requests.get(f"{BIOREACTOR_HUB_URL}/api/experiments/{experiment_id}/status")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    experiment_status = status_data.get("experiment", {}).get("status")
                    
                    if experiment_status in ["completed", "failed", "stopped"]:
                        print(f"   Experiment {experiment_status}: {experiment_id}")
                        
                        # Get results
                        results_response = requests.get(f"{BIOREACTOR_HUB_URL}/api/experiments/{experiment_id}/results")
                        if results_response.status_code == 200:
                            results_data = results_response.json()
                            print(f"   Results: {results_data}")
                        
                        break
                else:
                    print(f"   Failed to get experiment status: {status_response.status_code}")
            
            # Clean up
            requests.delete(f"{BIOREACTOR_HUB_URL}/api/experiments/{experiment_id}")
            print(f"   Experiment cleaned up: {experiment_id}")
            
        else:
            print(f"❌ Failed to start experiment: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Experiment workflow test failed: {e}")

def main():
    """Run all tests"""
    print("🚀 Starting Bioreactor System Tests\n")
    
    # Test bioreactor-node
    node_ok = test_bioreactor_node()
    
    # Test bioreactor-hub
    hub_ok = test_bioreactor_hub()
    
    # Test experiment workflow if both components are working
    if node_ok and hub_ok:
        test_experiment_workflow()
    
    print("\n🎉 Test completed!")
    
    if node_ok and hub_ok:
        print("✅ All components are working correctly")
        return 0
    else:
        print("❌ Some components failed - check the logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
