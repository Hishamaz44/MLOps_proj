#!/bin/bash

URL="http://localhost:8000/analyze_code"
TOTAL_REQUESTS=100


echo "Sending $TOTAL_REQUESTS concurrent requests with AI bypassed (dry_run=true)..."

START_TIME=$(date +%s)

for ((i=1; i<=TOTAL_REQUESTS; i++))
do
  # Notice the dry_run parameter is set to true
  curl -s -X POST "$URL" \
    -H "Content-Type: application/json" \
    -d "{\"code_input\": \"print('load test $i')\", \"dry_run\": true}" \
    -o /dev/null & 
done

echo "Waiting for the API to process the queue."
wait

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))


echo "Processed $TOTAL_REQUESTS requests in $DURATION seconds."
