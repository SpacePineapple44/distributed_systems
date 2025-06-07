import os
import time
import logging
import consul
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# In-memory list for replicated messages on this secondary
replicated_messages = []

# Consul configuration
CONSUL_HOST = os.getenv('CONSUL_HOST', 'consul')
CONSUL_PORT = int(os.getenv('CONSUL_PORT', '8500'))
SERVICE_NAME = 'secondary-log-service'
SERVICE_PORT = int(os.getenv('SECONDARY_PORT', '5001')) # Each secondary instance will have a different port
# Unique ID for each instance to register with Consul
SERVICE_ID = f"{SERVICE_NAME}-{os.getenv('HOSTNAME', 'localhost')}-{SERVICE_PORT}"

# Initialize Consul client
c = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)

@app.route('/replicate', methods=['POST'])
def replicate_message():
    """Receives a message from the Master for replication."""
    message = request.json.get('message')
    if not message:
        return jsonify({"error": "Message is required"}), 400

    logging.info(f"Secondary ({SERVICE_ID}) received replicated message: '{message}'")

    # Simulate delay/sleep as per the task requirement for testing blocking replication
    delay = int(os.getenv('REPLICATION_DELAY_SEC', '0'))
    if delay > 0:
        logging.info(f"Secondary ({SERVICE_ID}) simulating delay for {delay} seconds...")
        time.sleep(delay)
        logging.info(f"Secondary ({SERVICE_ID}) delay finished.")

    replicated_messages.append(message) # Append message to this secondary's local log
    return jsonify({"status": "success", "message": "Message replicated successfully"}), 200

@app.route('/list_replicated_msgs', methods=['GET'])
def list_replicated_messages():
    """Returns the list of replicated messages on this Secondary."""
    logging.info(f"Secondary ({SERVICE_ID}) received request to list replicated messages.")
    return jsonify({"messages": replicated_messages}), 200

def register_service():
    """Registers the Secondary service with Consul."""
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
