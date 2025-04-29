# Use Alpine-based Python image for a smaller attack surface
FROM python:3.12-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install necessary build tools for Python package compilation
RUN apk add --no-cache gcc musl-dev linux-headers python3-dev

# Upgrade pip and setuptools to the latest versions
RUN pip install --upgrade pip setuptools

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Use a virtual environment for better isolation
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "run.py"]