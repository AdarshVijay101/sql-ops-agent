# Deploy to Azure Container Apps

This project is configured to deploy as a public API to [Azure Container Apps (ACA)](https://learn.microsoft.com/en-us/azure/container-apps/overview) using the Consumption (serverless) plan. The consumption plan scales to zero, costing nothing when unused, making it an excellent free-tier architecture for this Agent.

## Architecture

*   **Compute**: Azure Container Apps (API + internal DuckDB + local RAG index)
*   **LLM Integration**: Defaults to `DEMO_MODE=1` to respond from a canned mock layer, avoiding costs for a live/cloud LLM while demonstrating capabilities.
*   **Container Registry**: GitHub Container Registry (GHCR) hosts the public Docker image.

## Prerequisite: GitHub Actions

The provided `.github/workflows/deploy-azure.yml` automates pushing the Docker image to GHCR and updating your Container App:

1.  Push your code to GitHub.
2.  Enable GitHub Actions. Wait for the `Build and Deploy` pipeline to push the image `ghcr.io/<your-user>/sql-ops-agent`.
3.  Ensure your package is public in GHCR settings if deploying a public image without managed identities.

## Deployment Instructions

Use the Azure CLI (`az`) to provision the container app environment and the app itself without Log Analytics to keep costs strictly at zero.

### 1. Login to Azure
```bash
az login
```

### 2. Create the Environment (Zero-Cost Logs)
```bash
az group create -n rg-sqlops -l eastus

az containerapp env create \
  --name env-sqlops \
  --resource-group rg-sqlops \
  --location eastus \
  --logs-destination none
```

### 3. Deploy the Container App
Run the following command, replacing `<your-gh-user>` with your GitHub username:

```bash
az containerapp create \
  --name sql-ops-agent \
  --resource-group rg-sqlops \
  --environment env-sqlops \
  --image ghcr.io/<your-gh-user>/sql-ops-agent:latest \
  --ingress external \
  --target-port 8080 \
  --env-vars DEMO_MODE=1 ALLOW_MOCK_FALLBACK=true \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

*This command outputs the public Fully Qualified Domain Name (FQDN).*

## Verification

Once deployed, use your FQDN to verify the endpoints.

**Health Check**:
```bash
curl https://<YOUR-FQDN>.azurecontainerapps.io/healthz
```

**Run Demo Agent**:
```bash
curl -X POST https://<YOUR-FQDN>.azurecontainerapps.io/v1/agent/run \
     -H "Content-Type: application/json" \
     -d '{"query": "Show me 5 users"}'
```
You should see a mock response that demonstrates RAG citations and Guardrail safety.

## Using a Real LLM in the Cloud
If you are willing to pay for a hosted OpenAI-compatible LLM (e.g. OpenAI, Azure OpenAI, Groq, or RunPod), set the environment variables on the app:

```bash
az containerapp update -n sql-ops-agent -g rg-sqlops \
  --set-env-vars DEMO_MODE=0 LLM_BASE_URL="https://api.openai.com/v1" LLM_API_KEY="<secret>" LLM_MODEL="gpt-4o-mini"
```
