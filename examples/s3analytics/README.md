# About
This example highlights how to synchronize to a S3 bucket which stores regular exports from DynamoDB. Additionally, a sample python has been included showing how these payloads could be read.


# Setup

`chmod +x sync_s3.sh`

**sample .env**
```
BUCKET=
```

**setup & use venv**
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


# Sample Run
```
export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""
export AWS_SESSION_TOKEN=""

./sync_s3.sh

python main.py
```