FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

# Install xvfb
RUN apt-get update && apt-get install -y xvfb && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run with xvfb-run to provide a virtual display
CMD ["xvfb-run", "--auto-servernum", "--server-args=-screen 0 1280x800x24", "python", "data_ingestion_service.py"]