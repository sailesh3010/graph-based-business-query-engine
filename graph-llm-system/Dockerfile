# Stage 1: Build the React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the Python backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for psycopg2 and other packages
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy the raw dataset so ingest.py can populate the DB on first run
COPY sap-o2c-data/ ./sap-o2c-data/

# Copy built frontend from Stage 1 into expected location
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Make entrypoint script executable
RUN chmod +x ./backend/entrypoint.sh

# Expose the API port
EXPOSE 8000

# Prevent python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Run the FastAPI server via entrypoint
WORKDIR /app/backend
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
