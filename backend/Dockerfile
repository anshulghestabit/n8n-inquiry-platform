# FastAPI development image for the backend API service.
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies before copying the app to improve Docker layer reuse.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run uvicorn with reload because this compose stack is used for local iteration.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
