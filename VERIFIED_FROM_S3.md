```markdown
# **Allianz MLOps Mock App Quick Start Guide**
*Automate AI-driven code analysis and documentation in just 3 steps*

---

## **Step 1: Set Up Your Environment**
Configure your system to run the MLOps Mock App.

### **Prerequisites**
- Install required packages:
  ```bash
  pip install fastapi uvicorn boto3 crewai pydantic prometheus-client
  ```
- Configure AWS credentials (if using S3):
  ```bash
  aws configure
  ```
- Ensure Ollama is running (for LLM access):
  ```bash
  ollama pull ministral-3:3b
  ```

### **Environment Variables**
Set these in your `.env` file or environment:
```env
CREWAI_DISABLE_TELEMETRY="1"
AWS_ACCESS_KEY_ID="your_access_key"
AWS_SECRET_ACCESS_KEY="your_secret_key"
```

---

## **Step 2: Initialize the Mock App**
Start the FastAPI server to begin processing requests.

### **Run the App**
```bash
uvicorn main:app --reload
```
- The app will be available at `http://localhost:8000`.
- Prometheus metrics are exposed at `/metrics`.

### **Key Features**
- **Metrics**: Track request counts, latency, and token usage.
- **S3 Integration**: Automatically uploads documentation to AWS S3.
- **AI Agents**: Uses `analyst` and `writer` Agents to generate documentation.

---

## **Step 3: Analyze and Document Code**
Submit code via the `/analyze_code` endpoint to generate a Quick Start Guide.

### **Example Request**
Send a POST request to `/analyze_code` with a JSON payload:
```json
{
  "code_input": "import os, time\nfrom crewai import Agent, Task\n\n# Example code snippet\nprint('Hello, world!')"
}
```

### **Response**
The endpoint returns a preview of the generated documentation:
```json
{
  "status": "success",
  "documentation_preview": "## **Allianz MLOps Mock App Quick Start Guide**\n\n### **Step 1: Set Up Your Environment**\n\nConfigure your system to run the MLOps Mock App..."
}
```

### **Next Steps**
1. **Review the Preview**: Check the truncated documentation preview.
2. **Upload to S3**: The app automatically uploads the full documentation to `allianz-docs` in S3.
3. **Monitor Metrics**: Check `/metrics` for request counts, latency, and token usage.

---

## **Key Features**
✅ **AI-Powered Analysis**: Extracts technical components from code.
✅ **Automated Documentation**: Generates a Quick Start Guide.
✅ **Centralized Storage**: Uploads results to AWS S3.
✅ **Comprehensive Monitoring**: Tracks performance metrics.

---

## **Troubleshooting**
- **S3 Errors**: Ensure AWS credentials are correct and the bucket `allianz-docs` exists.
- **Ollama Errors**: Verify Ollama is running and the model `ministral-3:3b` is downloaded.
- **Metrics Issues**: Check `/metrics` for detailed error logs.

---
*© Allianz UX Department | Simplified for everyone*
```