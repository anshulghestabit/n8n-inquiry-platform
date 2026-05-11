# FastAPI development image for the backend API service.
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies from the committed uv lockfile before copying
# the app source to keep Docker layer reuse and dependency resolution stable.
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.11.13 \
    && uv export --quiet --locked --no-dev --format requirements.txt --no-emit-project --output-file /tmp/requirements.lock \
    && uv pip install --system --no-cache -r /tmp/requirements.lock \
    && rm /tmp/requirements.lock

# Copy only runtime source files. Avoid recursive context copies so local
# secrets or generated files cannot be baked into the image by accident.
COPY main.py ./
COPY app ./app
COPY templates ./templates

# Run uvicorn with reload because this compose stack is used for local iteration.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
