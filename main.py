import os
import time
from crewai import Agent, Task, Crew, Process, LLM 
import boto3 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import make_asgi_app, Counter, Histogram
import contextlib
import io

os.environ["CREWAI_DISABLE_TELEMETRY"] = "1" # Add this to stop CrewAI from phoning home!
# 1. Initilialize FastAPI app
app = FastAPI(title='MLOps Mock App')

# 2. Initialize the class
class AnalysisRequest(BaseModel):
    code_input: str
    dry_run: bool = False

class DebateRequest(BaseModel):
    debate_topic: str
    dry_run: bool = False

# Gauge 1
REQUEST_COUNT = Counter(
    'ai_requests_total',
    'Total AI requests processed',
    ['endpoint', 'http_status'],
    
)
# Gauge 2: The Latency Histogram (Tracks speed)
REQUEST_LATENCY = Histogram(
    'ai_request_latency_seconds', 
    'Time spent processing the AI request', 
    ['endpoint'],
    buckets=[1.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0, float("inf")] # Custom time buckets
)

# Gauge 3: The Token Histogram (Tracks cost/usage)
TOKEN_USAGE = Histogram(
    'ai_tokens_consumed', 
    'Distribution of tokens consumed per request', 
    ['model'],
    buckets=[50, 100, 250, 500, 1000, 2000, 5000, float("inf")] # Custom token buckets
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# 3. Initialize the S3 Client (Global scope)
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)


# 4.1 Use CrewAI's native LLM class with the 'ollama/' prefix and your local base URL
local_llm = LLM(
    model="ollama/ministral-3:3b",
    base_url="http://localhost:11434"
)

print("--- Initializing Agents ---")

#  AGENT DEFINITIONS
analyst = Agent(
    role='Senior Technical Analyst',
    goal='Analyze the provided Python code and identify its core logic and functions.',
    backstory="""You are an expert at breaking down complex code. You identify 
    the "how" and "what" of a script so it can be documented accurately.""",
    llm=local_llm, # <-- Pass the native LLM object here
    verbose=True,
    allow_delegation=False
)

writer = Agent(
    role='UX Documentation Specialist',
    goal='Create a simple, trustworthy Quick Start Guide for the analyzed code.',
    backstory="""You work for Allianz's UX department. Your mission is to make 
    complex technical products simple and accessible for everyone.""",
    llm=local_llm, # <-- Pass the native LLM object here
    verbose=True,
    allow_delegation=False
)


# Debate Agents 
proponent = Agent(
    role='Enthusiastic Advocate',
    goal='Argue passionately IN FAVOR of the provided topic.',
    backstory="You are a master debater who focuses on the positive aspects, benefits, and progressive nature of the topic.",
    llm=local_llm,
    verbose=True,
    allow_delegation=False
)

opponent = Agent(
    role='Fierce Critic',
    goal='Read the advocate\'s argument and aggressively argue AGAINST the topic. ',
    backstory="You are a skeptical, pragmatic critic. You look for flaws, risks, and historical failures to dismantle arguments.",
    llm=local_llm,
    verbose=True,
    allow_delegation=False
)


def upload_and_verify(content: str) -> bool:
    bucket_name = "allianz-docs"
    file_key = "quickstart.md"

    # Create bucket
    try:
        s3_client.create_bucket(Bucket=bucket_name)
    except:
        pass 

    # Upload
    s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=content)
    print(f"✅ Successfully saved to Mock S3 (LocalStack)!")
    # Download Verification (The part that errored before)
    try:
        s3_client.download_file(bucket_name, file_key, 'VERIFIED_FROM_S3.md')
        print(f"Downloaded 'VERIFIED_FROM_S3.md' back from the cloud!")
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        return False




@app.post("/debate")
async def trigger_debate(request: DebateRequest):
    start_time = time.time()

    # --- SRE MOCK MODE (For your 100-request stress test) ---
    if request.dry_run:
        time.sleep(0.05) # Tiny delay for the Grafana latency chart
        REQUEST_COUNT.labels(endpoint='/debate', http_status=200).inc()
        REQUEST_LATENCY.labels(endpoint='/debate').observe(time.time() - start_time)
        return {"status": "success", "message": "DRY RUN: Debate bypassed for load testing."}

    # --- 1. THE TASKS ---
    pro_task = Task(
        description=f"Write a strong, 1-paragraph opening statement IN FAVOR of: {request.debate_topic}",
        expected_output="A persuasive 1-paragraph argument.",
        agent=proponent
    )

    con_task = Task( # CrewAI automatically passes pro_task's output into this one!
        description="Read the opening statement provided. Write a fierce 1-paragraph rebuttal tearing down their argument.",
        expected_output="A critical 1-paragraph rebuttal.",  
        agent=opponent
    )

    # --- 2. THE CREW ---
    debate_crew = Crew(
        agents=[proponent, opponent],
        tasks=[pro_task, con_task],
        process=Process.sequential,
        verbose=True
    )

    # --- 3. EXECUTION & METRICS ---
    try:
        await debate_crew.kickoff_async()
        
        pro_argument = str(pro_task.output)
        con_argument = str(con_task.output)

        transcript = (
            f"# Debate Topic:  {request.debate_topic} \n\n"
            f"## Proponent's Argument: \n {pro_argument} \n"
            f"## Opponent's Argument: \n {con_argument} \n"
        )

        s3_success = upload_and_verify(transcript)

        if not s3_success:
            # This records the counter and the Latency
            REQUEST_COUNT.labels(endpoint='/debate', http_status=500).inc()
            REQUEST_LATENCY.labels(endpoint='/debate').observe(time.time() - start_time)
            raise HTTPException(status_code=500, detail="AI succeeded, but S3 upload did not")
        
        # This records the counter and the Latency
        REQUEST_COUNT.labels(endpoint='/debate', http_status=200).inc()
        REQUEST_LATENCY.labels(endpoint='/debate').observe(time.time() - start_time)

        # This records the amount of tokens generated by the AI models
        estimated_tokens = len(transcript) // 4
        TOKEN_USAGE.labels(model='ministral-3:3b').observe(estimated_tokens)

        # Return the response to the user
        return {
            "status": "success",
            "message": "Subject debated successfully",
            "s3_bucket": "allianz-docs",
            "documentation_preview": transcript[:200] + "..."
        }
    except Exception as e:
    # Handle AI crashes: If the AI or CrewAI crashes, record a 500 error
        REQUEST_COUNT.labels(endpoint='/debate', http_status=500).inc()
        REQUEST_LATENCY.labels(endpoint='/debate').observe(time.time() - start_time)
        raise HTTPException(status_code=500, detail=f"AI crashed. Error is {str(e)}")







@app.post("/analyze_code")
async def analyze_code(request: AnalysisRequest):
    # 4. TASK DEFINITIONS

    start_time = time.time()

    # SRE Simulation Mode
    if request.dry_run: 
        time.sleep(0.1)
        results_str = "DRY RUN: This is a simulated AI response for load testing"
        REQUEST_COUNT.labels(endpoint='/analyze_code', http_status=200).inc()
        REQUEST_LATENCY.labels(endpoint='/analyze_code').observe(time.time() - start_time)

        return {
            'status': 'success',
            'message': 'DRY RUN',
            's3_bucket': 'skipped'
        }

    analysis_task = Task(
        description=f"""Carefully read this code snippet:
        {request.code_input}
        
        List the main functions and what the inputs/outputs are.""",
        expected_output="A bulleted list of technical components and logic flow.",
        agent=analyst
    )

    writing_task = Task(
        description="""Based on the technical analysis, write a 3-step 'Quick Start Guide'. 
        Use simple language. Make it look professional in Markdown format.""",
        expected_output="A Markdown formatted Quick Start Guide ready for a README file.",  
        agent=writer
    )

    # 5. THE CREW (The Orchestration)
    documentation_crew = Crew(
        agents=[analyst, writer],
        tasks=[analysis_task, writing_task],
        process=Process.sequential,
        verbose=True
    )

    try:
        result = await documentation_crew.kickoff_async()
        result_str = str(result)

        s3_success = upload_and_verify(result_str)

        if not s3_success:
            # This records the counter and the Latency
            REQUEST_COUNT.labels(endpoint='/analyze_code', http_status=500).inc()
            REQUEST_LATENCY.labels(endpoint='/analyze_code').observe(time.time() - start_time)
            raise HTTPException(status_code=500, detail="AI succeeded, but S3 upload did not")
        
        # This records the counter and the Latency
        REQUEST_COUNT.labels(endpoint='/analyze_code', http_status=200).inc()
        REQUEST_LATENCY.labels(endpoint='/analyze_code').observe(time.time() - start_time)

        # This records the amount of tokens generated by the AI models
        estimated_tokens = len(result_str) // 4
        TOKEN_USAGE.labels(model='ministral-3:3b').observe(estimated_tokens)

        # Return the response to the user
        return {
            "status": "success",
            "message": "Code analyzed and documentation saved to S3.",
            "s3_bucket": "allianz-docs",
            "documentation_preview": result_str[:200] + "..."
        }
    except Exception as e:
    # Handle AI crashes: If the AI or CrewAI crashes, record a 500 error
        REQUEST_COUNT.labels(endpoint='/analyze_code', http_status=500).inc()
        REQUEST_LATENCY.labels(endpoint='/analyze_code').observe(time.time() - start_time)
        raise HTTPException(status_code=500, detail=f"AI crashed. Error is {str(e)}")