#!/bin/bash

# Configuration
URL="http://localhost:8000/analyze_code"
CONCURRENT_REQUESTS=4

# Different code snippets to analyze
CODE_SAMPLES=(
    "def hello(): print('world')"
    "def add(a, b): return a + b"
    "class User: def __init__(self, name): self.name = name"
    "import os; print(os.listdir('.'))"
)

echo "Simulating concurrent code analysis requests..."


# Start the timer
START_TIME=$(date +%s)

for i in {0..3}
do
  SAMPLE=${CODE_SAMPLES[$i]}
  echo "Request $((i+1)): Analyzing snippet '$SAMPLE'"
  
  # Send request to background
  curl -s -X POST "$URL" \
    -H "Content-Type: application/json" \
    -d "{\"code_input\": \"$SAMPLE\"}" \
    -o /dev/null & 
done

echo "The AI Agents are working."
wait # Wait for the background processes to finish

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "TEST COMPLETE"
echo "Total Time: $DURATION seconds"
