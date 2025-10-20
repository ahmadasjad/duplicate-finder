# Base Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app

# Set the working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install minimal system dependencies needed to fetch rclone and provide FUSE support.
# Use noninteractive frontend and install curl to satisfy the rclone installer; clean apt caches
# promptly to minimize build disk usage.
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install -y --no-install-recommends fuse3 wget curl ca-certificates unzip && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* && \
    # Install rclone via official install script (streamed); keep logs quiet
    wget -qO- https://rclone.org/install.sh | bash && \
    # Install Python requirements
    pip install --no-cache-dir -r requirements.txt && \
    # Final cleanup
    apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Create mount directory for Google Drive
RUN mkdir -p /mnt/gdrive && chown -R 1000:1000 /mnt/gdrive

# Expose Streamlit's default port
EXPOSE 8501

# Copy container entrypoint (optional script will handle mount lifecycle)
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use entrypoint so mount/unmount hooks can run; default command runs Streamlit
ENTRYPOINT ["/entrypoint.sh"]
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
