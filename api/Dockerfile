FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code. The build context is the repo root; .dockerignore
# keeps frontend/, tests/, .venv/, .git/ and secrets out of the image.
COPY . .

# Expose port
EXPOSE 8000

# NOTE: no --reload here. docker-compose bind-mounts the source for editing,
# but the server must be restarted to pick changes up.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
