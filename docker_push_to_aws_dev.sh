aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 992382623268.dkr.ecr.us-east-1.amazonaws.com
docker build -t cdk-ecr-stack-dev-waterbot7e9d62bf-ecu5fqeoy7g1 .
docker tag cdk-ecr-stack-dev-waterbot7e9d62bf-ecu5fqeoy7g1:latest 992382623268.dkr.ecr.us-east-1.amazonaws.com/cdk-ecr-stack-dev-waterbot7e9d62bf-ecu5fqeoy7g1:latest
docker push 992382623268.dkr.ecr.us-east-1.amazonaws.com/cdk-ecr-stack-dev-waterbot7e9d62bf-ecu5fqeoy7g1:latest