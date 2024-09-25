#!/bin/sh

# Check if AWS_ACCESS_KEY_ID is set
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "AWS_ACCESS_KEY_ID is not set"
    exit 1
fi

# Check if AWS_ACCESS_KEY_ID is set
if [ -z "$AWS_DEFAULT_REGION" ]; then
    export AWS_DEFAULT_REGION="us-east-1"
fi

# Check if AWS_SECRET_ACCESS_KEY is set
if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "AWS_SECRET_ACCESS_KEY is not set"
    exit 1
fi

# Check if AWS_SESSION_TOKEN is set
if [ -z "$AWS_SESSION_TOKEN" ]; then
    echo "AWS_SESSION_TOKEN is not set"
    exit 1
fi

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "OPENAI_API_KEY is not set"
    exit 1
fi

# Check if MESSAGES_TABLE is set
if [ -z "$MESSAGES_TABLE" ]; then
    echo "MESSAGES_TABLE is not set"
    exit 1
fi

# Run the Docker container if all environment variables are set
docker run -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
           -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
           -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
           -e AWS_DEFAULT_REGION="$AWS_DEFAULT_REGION" \
           -e OPENAI_API_KEY="$OPENAI_API_KEY" \
           -e MESSAGES_TABLE="$MESSAGES_TABLE" \
           -p 8000:8000 waterbot