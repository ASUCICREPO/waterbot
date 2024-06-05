from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    SecretValue,
    aws_elasticloadbalancingv2 as elbv2,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_dynamodb as dynamodb
)
import os


class AppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, imports: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the secret value from an environment variable
        secret_value = os.environ.get("OPENAI_API_KEY")
        if not secret_value:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # Get the secret value from an environment variable
        secret_header_value = os.environ.get("SECRET_HEADER_KEY")
        if not secret_header_value:
            raise ValueError("SECRET_HEADER_KEY environment variable is not set")
        
        # Get the secret value from an environment variable
        basic_auth_secret = os.environ.get("BASIC_AUTH_SECRET")
        if not basic_auth_secret:
            raise ValueError("BASIC_AUTH_SECRET environment variable is not set -- base64 encode of uname:pw")
        

        dynamo_messages = dynamodb.Table(self,"cdk-waterbot-messages",
            partition_key=dynamodb.Attribute(name="sessionId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="msgId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # Create a VPC for the Fargate cluster
        vpc = ec2.Vpc(self, "WaterbotVPC", max_azs=2)

        # Get the repository URL
        repository = imports["repository"]

        # Create the Fargate cluster
        cluster = ecs.Cluster(
            self, "WaterbotFargateCluster",
            vpc=vpc
        )

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
        #         We will likely want different approach   #
        #         for production as this will have secret  #
        #         in plaintext of CDK outputs              #
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
        # Create a Secrets Manager secret
        secret = secretsmanager.Secret(
            self, "OpenAI-APIKey",
            description="Open API Key",
            secret_string_value=SecretValue.unsafe_plain_text(secret_value)
        )

        # Create a task definition for the Fargate service
        task_definition = ecs.FargateTaskDefinition(
            self, "WaterbotTaskDefinition",
            memory_limit_mib=512,
            cpu=256,
        )
        # Grant the task permission to log to CloudWatch
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )

        # Grant the task permission to invoke Amazon Bedrock models
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],  # Replace with appropriate resource ARNs
            )
        )

        # Grant the task permission to access the secret
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[secret.secret_arn]
            )
        )

        # Grant the task permission to access dynamodb
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[            
                    "dynamodb:BatchGetItem",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWriteItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem"
                ],
                resources=[dynamo_messages.table_arn], 
            )
        )

        # Create a container in the task definition & inject the secret into the container as an environment variable
        container = task_definition.add_container(
            "WaterbotAppContainer",
            image=ecs.ContainerImage.from_ecr_repository(repository, tag="latest"),
            port_mappings=[ecs.PortMapping(container_port=8000)],
            environment={
                "MESSAGES_TABLE": dynamo_messages.table_name
            },
            secrets={
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(secret)
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/ || exit 1"],
                interval=Duration.minutes(1),
                timeout=Duration.seconds(5),
                retries=3,
            )
        )

        # Create an Application Load Balancer
        alb_wb = elbv2.ApplicationLoadBalancer(
            self, "FargateALB",
            vpc=vpc,
            internet_facing=True
        )

        # Create a listener for the ALB
        listener_wb = alb_wb.add_listener(
            "FargateALBListener",
            port=80,
            open=True
        )


        # Create a target group for the Fargate service
        target_group_wb = listener_wb.add_targets(
            "FargateTargetGroup",
            port=8000,
            targets=[ecs.FargateService(
                self, "FargateService",
                cluster=cluster,
                task_definition=task_definition,
                desired_count=3,
            )],
            health_check=elbv2.HealthCheck(
                path="/",
                interval=Duration.minutes(1),
                timeout=Duration.seconds(5)
            ),
            stickiness_cookie_duration=Duration.hours(2),  # Set the cookie duration
            stickiness_cookie_name="WATERBOT"  # Set the cookie name
        )


        # overwrite default action implictly created above (will cause warning)
        listener_wb.add_action(
            "Default",
            action=elbv2.ListenerAction.fixed_response(
                status_code=403,
                content_type="text/plain",
                message_body="Forbidden"
            )
        )

        # Create a rule to check for the custom header
        custom_header_rule = elbv2.ApplicationListenerRule(
            self, "CustomHeaderRule",
            listener=listener_wb,
            priority=1,
            conditions=[
                elbv2.ListenerCondition.http_header(
                    name='X-Custom-Header',
                    values=[secret_header_value],
                )
            ],
            action=elbv2.ListenerAction.forward(
                target_groups=[target_group_wb]
            )
        )


        # Define the CloudFront Function inline
        # Note, secret will be exposed plaintext in CDK logs as well as
        # edge function
        #
        # This is just a basic auth blocker to help prevent genai llm call misuse
        basic_auth_function_code = """
            function handler(event) {
            var authHeaders = event.request.headers.authorization;
            var expected = "Basic """ + basic_auth_secret
        
        basic_auth_function_code += """";

            // If an Authorization header is supplied and it's an exact match, pass the
            // request on through to CF/the origin without any modification.
            if (authHeaders && authHeaders.value === expected) {
                return event.request;
            }

            // But if we get here, we must either be missing the auth header or the
            // credentials failed to match what we expected.
            // Request the browser present the Basic Auth dialog.
            var response = {
                statusCode: 401,
                statusDescription: "Unauthorized",
                headers: {
                "www-authenticate": {
                    value: 'Basic realm="Enter credentials for this super secure site"',
                },
                },
            };

            return response;
            }
        """

        basic_auth_function = cloudfront.Function(
            self, "BasicAuthFunction",
            code=cloudfront.FunctionCode.from_inline(basic_auth_function_code),
            function_name="BasicAuthFunction",
        )



        # Create a CloudFront distribution with the ALB as the origin
        cloudfront_distribution_wbot = cloudfront.Distribution(
            self, "CloudFrontDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.LoadBalancerV2Origin(
                    alb_wb,
                    origin_path="/",
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                    custom_headers={
                        "X-Custom-Header": secret_header_value
                    },
                ),
                function_associations=[
                    cloudfront.FunctionAssociation(
                        event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                        function=basic_auth_function,
                    )
                ],
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
            enabled=True,
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=403,
                    response_page_path="/error.html",
                    ttl=Duration.minutes(30),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=404,
                    response_page_path="/error.html",
                    ttl=Duration.minutes(30),
                ),
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
        )

