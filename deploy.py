import os
import subprocess
import sys

# Load environment variables securely
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN environment variable not set.")
    sys.exit(1)

# Check for local changes
status_output = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
if status_output.stdout:
    print("Error: There are uncommitted changes. Please commit or stash your changes before deploying.")
    sys.exit(1)

# Variables
REPO_URL = f"https://{GITHUB_TOKEN}@github.com/toddllm/softwarecompanyinabox.git"
DOCKER_IMAGE = "softwarecompanyinabox:latest"
CONTAINER_NAME = "softwarecompanyinabox"
DOCKER_PORT = 3000
HOST_PORT = 8080
NGINX_CONFIG_PATH = "/etc/nginx/sites-available/softwarecompanyinabox"

# SSH command to execute the deployment steps
ssh_command = f"""
ssh aws-vm1 << EOF
    APP_DIR=\$(pwd)/softwarecompanyinabox

    # Ensure the application directory exists
    if [ -d "\$APP_DIR" ]; then
        cd \$APP_DIR
        git pull origin main
    else
        git clone {REPO_URL} \$APP_DIR
        cd \$APP_DIR
    fi

    # Build the Docker image
    sudo docker build -t {DOCKER_IMAGE} .

    # Stop the existing container if it exists
    if [ \$(sudo docker ps -aq -f name={CONTAINER_NAME}) ]; then
        if [ \$(sudo docker ps -q -f name={CONTAINER_NAME}) ]; then
            sudo docker stop {CONTAINER_NAME}
        fi
        sudo docker rm {CONTAINER_NAME}
    fi

    # Run the Docker container on a different port
    sudo docker run -d --name {CONTAINER_NAME} -p {HOST_PORT}:{DOCKER_PORT} {DOCKER_IMAGE}

    # Check if Nginx config exists
    if [ -f "{NGINX_CONFIG_PATH}" ]; then
        if ! grep -q "proxy_pass http://localhost:{DOCKER_PORT};" "{NGINX_CONFIG_PATH}"; then
            sudo tee -a "{NGINX_CONFIG_PATH}" > /dev/null <<EOL
location / {{
    proxy_pass http://localhost:{DOCKER_PORT};
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
}}
EOL
            sudo systemctl reload nginx
        fi
    else
        sudo tee "{NGINX_CONFIG_PATH}" > /dev/null <<EOL
server {{
    listen 80;
    server_name softwarecompanyinabox.com www.softwarecompanyinabox.com;

    location / {{
        proxy_pass http://localhost:{DOCKER_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }}
}}
EOL
        sudo ln -s "{NGINX_CONFIG_PATH}" /etc/nginx/sites-enabled/
        sudo systemctl reload nginx
    fi
EOF
"""

# Execute the SSH command
subprocess.run(ssh_command, shell=True, check=True)

