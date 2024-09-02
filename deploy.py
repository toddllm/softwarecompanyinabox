import os
import subprocess
import sys

def run_remote_command(command):
    print(f"Running command: {command}")
    result = subprocess.run(f"ssh aws-vm1 {command}", shell=True, text=True, capture_output=True)
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")
    if result.returncode != 0:
        print(f"Error running command: {command}")
        sys.exit(1)
    return result.stdout.strip()

# Load environment variables securely
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN environment variable not set.")
    sys.exit(1)

# Check for local changes
print("Checking for local changes...")
status_output = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
if status_output.stdout:
    print("Error: There are uncommitted changes. Please commit or stash your changes before deploying.")
    sys.exit(1)

# Variables
REPO_URL = f"https://{GITHUB_TOKEN}@github.com/toddllm/softwarecompanyinabox.git"
DOCKER_IMAGE = "softwarecompanyinabox:latest"
CONTAINER_NAME = "softwarecompanyinabox"
DOCKER_PORT = 3000
HOST_PORT = 3000
NGINX_CONFIG_PATH = "/etc/nginx/sites-available/softwarecompanyinabox"

# Ensure the application directory exists and pull the latest changes
print("Ensuring application directory exists and pulling latest changes...")
run_remote_command(f"""
    if [ -d softwarecompanyinabox ]; then
        cd softwarecompanyinabox && git pull origin main
    else
        git clone {REPO_URL} softwarecompanyinabox
    fi
""")

# Build the Docker image
print("Building Docker image...")
run_remote_command(f"""
    cd softwarecompanyinabox && sudo docker build -t {DOCKER_IMAGE} .
""")

# Stop and remove the existing Docker container if it exists
print("Stopping and removing existing Docker container (if any)...")
existing_container = run_remote_command(f"sudo docker ps -aq -f name={CONTAINER_NAME}")
if existing_container:
    run_remote_command(f"""
        sudo docker stop {CONTAINER_NAME}
        sudo docker rm {CONTAINER_NAME}
    """)

# Run the Docker container
print("Running Docker container...")
run_remote_command(f"""
    sudo docker run -d --name {CONTAINER_NAME} -p {HOST_PORT}:{DOCKER_PORT} {DOCKER_IMAGE}
""")

# Check if the Docker container is running
print("Checking if Docker container is running...")
container_running = run_remote_command(f"sudo docker ps -q -f name={CONTAINER_NAME}")
if not container_running:
    print(f"Error: Docker container {CONTAINER_NAME} is not running.")
    sys.exit(1)

# Check if the service inside the container is listening on the expected port
print("Checking if service inside Docker container is listening on the expected port...")
service_listening = run_remote_command(f"sudo docker exec {CONTAINER_NAME} netstat -tuln | grep :{DOCKER_PORT}")
if not service_listening:
    print(f"Error: Service inside the Docker container is not listening on port {DOCKER_PORT}.")
    print("Docker container logs:")
    print(run_remote_command(f"sudo docker logs {CONTAINER_NAME}"))
    sys.exit(1)

# Update Nginx configuration if necessary
print("Checking and updating Nginx configuration...")
nginx_config_exists = run_remote_command(f"if [ -f {NGINX_CONFIG_PATH} ]; then echo exists; fi")
if nginx_config_exists:
    proxy_config_exists = run_remote_command(f"grep -q 'proxy_pass http://localhost:{DOCKER_PORT};' {NGINX_CONFIG_PATH}")
    if not proxy_config_exists:
        run_remote_command(f"""
            sudo tee -a {NGINX_CONFIG_PATH} > /dev/null <<EOL
location / {{
    proxy_pass http://localhost:{DOCKER_PORT};
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}}
EOL
            sudo systemctl reload nginx
        """)
else:
    run_remote_command(f"""
        sudo tee {NGINX_CONFIG_PATH} > /dev/null <<EOL
server {{
    listen 80;
    server_name softwarecompanyinabox.com www.softwarecompanyinabox.com;

    location / {{
        proxy_pass http://localhost:{DOCKER_PORT};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
EOL
        sudo ln -s {NGINX_CONFIG_PATH} /etc/nginx/sites-enabled/
        sudo systemctl reload nginx
    """)

# Check if Nginx is running and listening on port 80
print("Checking if Nginx is running and listening on port 80...")
nginx_listening = run_remote_command("sudo netstat -tuln | grep :80")
if not nginx_listening:
    print("Error: Nginx is not running or not listening on port 80.")
    sys.exit(1)

print("Deployment completed successfully. All checks passed.")

