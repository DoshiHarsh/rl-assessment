# Step 1: Use an official Python runtime as a parent image
FROM python:3.9-slim

# Step 2: Set the working directory in the container
WORKDIR /app

# Step 3: Copy the current directory contents into the container at /app
COPY . /app

# Step 4: Install any needed packages specified in requirements.txt
# First, create the requirements.txt if not already created
RUN pip install --no-cache-dir grpcio grpcio-tools

# Step 5: Make port 50051 available to the world outside this container
EXPOSE 50055

# Step 6: Run server.py when the container launches
CMD ["python", "server.py"]
