FROM python:3.12-slim

# TZ: Singapore time, so "today" in the container matches the workers' date (the default clock is UTC, 8 hours behind)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Singapore

WORKDIR /app

# Copy Dependencies Txt File
COPY requirements.txt .

# Tkinter, plus fonts for every language on the welcome screen
RUN apt-get update && apt-get install -y --no-install-recommends python3-tk fontconfig fonts-noto-core fonts-noto-cjk && rm -rf /var/lib/apt/lists/*

# Install Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a Directory for Data Files
COPY . .
RUN mkdir -p data

# Load the API key from the copied .env file (unless one was already passed in with --env-file or -e)
CMD ["sh", "-c", "if [ -z \"$GEMINI_API_KEY\" ] && [ -f .env ]; then export $(grep -v '^#' .env | tr -d '\\r' | xargs); fi; exec python main.py"]