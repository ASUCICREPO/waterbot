# Disclaimers

**Customers are responsible for making their own independent assessment of the information in this document and repository.**

**This document and repository:**

(a) is for informational purposes only, 

(b) represents current AWS product offerings and practices, which are subject to change without notice, and 

(c) does not create any commitments or assurances from AWS and its affiliates, suppliers or licensors. AWS products or services are provided “as is” without warranties, representations, or conditions of any kind, whether express or implied. The responsibilities and liabilities of AWS to its customers are controlled by AWS agreements, and this document is not part of, nor does it modify, any agreement between AWS and its customers. 

(d) is not to be considered a recommendation or viewpoint of AWS

**Additionally, all prototype code and associated assets should be considered:**

(a) as-is and without warranties

(b) not suitable for production environments

(d) to include shortcuts in order to support rapid prototyping such as, but not limited to, relaxed authentication and authorization processes

**All work produced is open source. More information can be found in the GitHub repo.**


# Waterbot

_Reference Site: https://waterbot-stream-bda64cf22bc1.herokuapp.com/_

# Note: Additional file in root:  ecr_auth.sh
**Not tracked on github; dynamic based on deploy.**

```bash
#!/bin/sh
aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {act_num}.dkr.ecr.{region}.amazonaws.com/{repo}
```

**Give it run permissions:** `chmod +x ecr_auth.sh`

# Prerequisites

**Grab additional software**
```bash
sudo apt-get install jq
```

**Set your environment variables**
```bash
export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""
export AWS_SESSION_TOKEN=""
export OPENAI_API_KEY=""
export SECRET_HEADER_KEY=""
export BASIC_AUTH_SECRET=""
export MESSAGES_TABLE=""
export CLUSTER_NAME=""
export SERVICE_NAME=""
```
_**Note:** You won't know CLUSTER_NAME, SERVICE_NAME, MESSAGES_TABLE until post deployment; these variables are only necessary for fargate_update_cluster.sh script_

# Choice: Run Locally (No Container)
```bash
cd application
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
fastapi dev main.py
````
_**Note:**   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, OPENAI_API_KEY, MESSAGES_TABLE must be set; you can place OPENAI_API_KEY and MESSAGES_TABLE in your .env file_

# Choice: Run Locally (In Container)
```bash
./docker_build.sh
./docker_run.sh
```

# Choice: Deploy to AWS
_**Note:** You will need CDK preqruisites._

_**Reference:**_ https://cdkworkshop.com/
```
1) Bootstrap CDK
2) cdk deploy cdk-ecr-stack
3) ./docker_build.sh
4) ./docker_run.sh (to test)
5) ./ecr_auth.sh
6) https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html
----> docker tag {container_id} {act_id}.dkr.ecr.us-east-1.amazonaws.com/{repo}:latest
----> docker push {act_id}.dkr.ecr.us-east-1.amazonaws.com/{repo}:latest
7) build rest of cdk stack
----> cdk deploy '*'
```

# Additional Information
The stack has the ability to deploy out multiple instances if necessary.  By default, env is null and CDK will deploy out a "cdk-{name}-stack"; if context is set, a new instance with "cdk-{name}-stack-{env} will deploy out

```bash
# Deploy for dev environment
cdk deploy --context env=dev

# Deploy for staging environment
cdk deploy --context env=staging

# Deploy for production environment
cdk deploy --context env=prod
```
