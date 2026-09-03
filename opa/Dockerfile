# Use the official OPA image from Docker Hub as the base image
FROM openpolicyagent/opa:latest

# Copy the local policy.rego file to the /policy directory in the container
COPY policy.rego /policy/policy.rego

# Expose port 8181 for OPA to be accessible
EXPOSE 8181

# Run OPA in server mode and listen on all interfaces
CMD ["run", "--server", "--addr=0.0.0.0:8181", "/policy/policy.rego"]
