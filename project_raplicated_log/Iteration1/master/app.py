import os
import requests
import time
import logging
import consul
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# In-memory list (replicated log)
replicated_log = []

# Consul configuration
CONSUL_HOST = os.getenv('CONSUL_HOST', 'consul')
CONSUL_PORT = int(os.getenv('CONSUL_PORT', '8500'))
SERVICE_NAME = 'master-log-service'
SERVICE_PORT = int(os.getenv('MASTER_PORT', '5000'))
SERVICE_ID = f"{SERVICE_NAME}-{os.getenv('HOSTNAME', 'localhost')}-{SERVICE_PORT}"

# Initialize Consul client
c = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)

@app.route('/append', methods=['POST'])
def append_message():
    message = request.json.get('message')
    if not message:
        return jsonify({"error": "Message is required"}), 400

    logging.info(f"Master received message: {message}")
    replicated_log.append(message) # Append to master's local log

    # Discover and replicate to all Secondaries (blocking replication)
    secondary_services = []
    try:
        # Get healthy secondary services from Consul
        _, services = c.health.service('secondary-log-service', passing=True)
        secondary_services = [
            f"http://{s['Service']['Address']}:{s['Service']['Port']}/replicate"
            for s in services
        ]
        logging.info(f"Discovered {len(secondary_services)} secondary services.")
    except Exception as e:
        logging.error(f"Error getting secondary services from Consul: {e}")
        return jsonify({"status": "error", "message": "Failed to discover secondary services"}), 500

    if not secondary_services:
        logging.warning("No secondary services found for replication. Message appended locally only.")
        # If no secondaries, append locally and return success as per the simplified requirement
        return jsonify({"status": "success", "message": "Message appended locally (no secondaries to replicate)"}), 200

    successful_replications = 0
    errors = []
    # Iterate through all discovered secondaries and attempt replication
    for secondary_url in secondary_services:
        try:
            logging.info(f"Attempting to replicate message to {secondary_url}")
            # Send POST request to secondary with the message
            response = requests.post(secondary_url, json={'message': message}, timeout=10) # Increased timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            successful_replications += 1
            logging.info(f"Successfully replicated to {secondary_url}")
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to replicate to {secondary_url}: {e}"
            logging.error(error_msg)
            errors.append(error_msg)

    # Master's POST request finishes only after receiving ACKs from all Secondaries
    if successful_replications == len(secondary_services):
        return jsonify({"status": "success", "message": "Message replicated to all secondaries and appended"}), 200
    else:
        # If not all secondaries acknowledged, return an error
        return jsonify({"status": "error", "message": f"Failed to replicate to all secondaries. Replicated {successful_replications}/{len(secondary_services)}. Errors: {errors}"}), 500

@app.route('/list_msgs', methods=['GET'])
def list_messages():
    """Returns the list of messages on the Master."""
    logging.info("Master received request to list messages.")
    return jsonify({"messages": replicated_log}), 200

def register_service():
    """Registers the Master service with Consul."""
    # Using 'host.docker.internal' for local testing on some Docker setups,
    # but 'HOSTNAME' (container's internal IP) is better for inter-container communication.
    # For Docker Compose, the service name 'master' will resolve correctly within the network.
    service_address = os.getenv('HOSTNAME', '127.0.0.1')
    try:
        c.agent.service.register(
            name=SERVICE_NAME,
            service_id=SERVICE_ID,
            address=service_address,
            port=SERVICE_PORT,
            check=consul.Check.http(f"http://{service_address}:{SERVICE_PORT}/health", interval="10s", timeout="5s")
        )
        logging.info(f"Service {SERVICE_NAME} (ID: {SERVICE_ID}) registered with Consul at {service_address}:{SERVICE_PORT}.")
    except Exception as e:
        logging.error(f"Failed to register service with Consul: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint for Consul health checks."""
    return "OK", 200

if __name__ == '__main__':
    # Give Consul a few seconds to start up before attempting registration
    time.sleep(5)
    register_service()
    # Run the Flask app
    app.run(host='0.0.0.0', port=SERVICE_PORT)
