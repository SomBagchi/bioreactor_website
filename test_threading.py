#!/usr/bin/env python3
"""
Test script to verify threading works in containerized environment
"""

import time
import logging
from bioreactor_client import Bioreactor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def led_job(bioreactor):
    """Job to blink LED every 2 seconds"""
    logger.info("LED job: toggling LED")
    # This would toggle the LED in real hardware
    # For now, just log the action

def temp_job(bioreactor):
    """Job to read temperature every 1 second"""
    try:
        temps = bioreactor.get_vial_temp()
        logger.info(f"Temperature job: vial temps = {temps}")
    except Exception as e:
        logger.error(f"Temperature job error: {e}")

def pump_job(bioreactor):
    """Job to control pump every 3 seconds"""
    logger.info("Pump job: setting pump flow")
    # This would control the pump in real hardware
    # For now, just log the action

if __name__ == "__main__":
    logger.info("Starting threading test...")
    
    try:
        with Bioreactor() as bioreactor:
            # Define jobs: (function, frequency_seconds, duration_seconds)
            jobs = [
                (led_job, 2.0, 30.0),      # LED job every 2s for 30s
                (temp_job, 1.0, 30.0),     # Temp job every 1s for 30s  
                (pump_job, 3.0, 30.0),     # Pump job every 3s for 30s
            ]
            
            logger.info("Starting jobs in parallel threads...")
            bioreactor.run(jobs)
            
            # Wait for jobs to complete
            logger.info("Waiting for jobs to complete...")
            time.sleep(35)  # Wait a bit longer than the longest job
            
            logger.info("All jobs completed!")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise 
