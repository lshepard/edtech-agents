FROM python:3.12-slim

WORKDIR /app

# Install uv for faster dependency installation
RUN pip install uv

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv pip install --system -e .

# Copy the rest of the application
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose the ports the app runs on
EXPOSE 3030 8090

# Command to run the application
CMD ["uvicorn", "app.main:app", "--reload", "--port", "3030", "--host", "0.0.0.0"] 