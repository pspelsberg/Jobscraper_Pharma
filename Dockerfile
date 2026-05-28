FROM python:3.11-slim

# Set timezone to Germany (Europe/Berlin)
ENV TZ=Europe/Berlin
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user to adhere to security best practices (least privilege)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser && \
    chown -R appuser:appgroup /app

COPY --chown=appuser:appgroup requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appgroup medice_job_bot.py .

# Switch to the non-root user
USER appuser

# Run unbuffered so logs print immediately in Docker console
CMD ["python", "-u", "medice_job_bot.py"]
