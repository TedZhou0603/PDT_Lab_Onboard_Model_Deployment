# Use your existing working Alpamayo image
FROM alpamayo1.5:working

# Set the working directory
WORKDIR /workspace/Alpamayo1.5/repo

# Copy your inference script into the container
COPY test_single_image.py /app/test_single_image.py

# Keep Python output visible
ENV PYTHONUNBUFFERED=1

# Start the Alpamayo inference script
CMD ["python3", "/app/test_single_image.py"]


