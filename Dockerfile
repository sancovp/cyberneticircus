FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency packages first to leverage Docker cache
COPY heaven-framework-repo /libs/heaven-framework-repo
COPY sdna-repo /libs/sdna-repo

# Install heaven-framework and sanctuary-dna
RUN pip install --no-cache-dir /libs/heaven-framework-repo
RUN pip install --no-cache-dir /libs/sdna-repo

# Install basic server requirements
RUN pip install --no-cache-dir fastapi uvicorn pydantic neo4j python-dotenv nest-asyncio docker

# Copy application folders
COPY cyberneticircus/cyberneticircus /app/cyberneticircus
COPY cyberneticircus/templates /app/templates
COPY cyberneticircus/specs /app/specs

# Set environment variables
ENV PYTHONPATH=/app/cyberneticircus:/app
ENV SCRATCH_WORKSPACE_DIR=/app
ENV PROJECT_DIR=/app

WORKDIR /app/cyberneticircus

EXPOSE 8000

CMD ["python", "web_server.py"]
