#!/bin/bash
set -e
 
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &
export DISPLAY=:99
sleep 2
 
echo "Display set to $DISPLAY"
echo "Starting ingestor..."
exec python data_ingestion_service.py
 