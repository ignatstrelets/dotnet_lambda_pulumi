import json
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
import pulumi_aws_apigateway as apigateway

config = pulumi.Config();

role = aws.iam.Role("role", 
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com",
            },
        }],
    }),
    managed_policy_arns=[
        aws.iam.ManagedPolicy.AWS_LAMBDA_BASIC_EXECUTION_ROLE])

custom_policy_arns = [
        config.require('customVpcPolicy'),
        config.require('customSecretsManagerPolicy')] 

attachments = [
        aws.iam.RolePolicyAttachment(f"rolePolicyAttachment-{i}",
            role=role.name,
            policy_arn=arn)
            for i, arn in enumerate(custom_policy_arns)]

vpc = aws.ec2.get_vpc(id=config.require('customVpcId'))

lambda_sg = aws.ec2.SecurityGroup(
        "lambda-sg",
        vpc_id=vpc.id,
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                from_port=80,
                to_port=80,
                protocol="tcp",
                cidr_blocks=["0.0.0.0/0"],
                ),
            aws.ec2.SecurityGroupIngressArgs(
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=[vpc.cidr_block]
                )    
        ],
        egress=[                                                                    
            aws.ec2.SecurityGroupEgressArgs(
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=[vpc.cidr_block], 
                ),
            ],
        )

code_s3_bucket = "..."

code_s3_key = "..."

fn = aws.lambda_.Function("fn",
    runtime="dotnet6",
    timeout=10,                      
    handler="LambdaDemo::LambdaDemo.Function::FunctionHandler",
    role=role.arn,
    s3_bucket=code_s3_bucket,
    s3_key=code_s3_key,
    source_code_hash=aws.s3.get_bucket_object(bucket=code_s3_bucket, key=code_s3_key).etag,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "SECRET_NAME" : config.require_secret('secretName')}),
    vpc_config=aws.lambda_.FunctionVpcConfigArgs(
        subnet_ids=[config.require('subnetPublicAId')],
        security_group_ids=[lambda_sg.id]
    ))

api = apigateway.RestAPI("api",
  routes=[
    apigateway.RouteArgs(path="/", method=apigateway.Method.GET, event_handler=fn)])

secrets_manager_vpc_endpoint = aws.ec2.VpcEndpoint("my_secrets_manager_vpc_endpoint",
        vpc_id=vpc.id,
        service_name="com.amazonaws."+aws.get_region().name+".secretsmanager",
        vpc_endpoint_type="Interface",
        private_dns_enabled=True,                                           
        subnet_ids=[config.require('subnetPublicAId')],
        security_group_ids=[lambda_sg.id],
        )

rds_sg = aws.ec2.SecurityGroup(
        "rds-sg",
        vpc_id=vpc.id,
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                from_port=5432, 
                to_port=5432, 
                protocol="tcp", 
                security_groups=[lambda_sg.id],
                ),
            ]
        )

rds_subnet_group = aws.rds.SubnetGroup('rds-subnet-group',
        subnet_ids=[
            config.require('subnetPrivateAId'),
            config.require('subnetPrivateBId')])

rds_instance = aws.rds.Instance('dotnet-psql',
        identifier='dotnet-psql',
        allocated_storage=20,
        storage_type='gp2',
        engine='postgres',
        engine_version='14.10',
        instance_class='db.t3.micro',
        name='postgres',
        username=config.require('dbUsername'),
        password=config.require_secret('dbPassword'),
        db_subnet_group_name=rds_subnet_group.name,
        vpc_security_group_ids=[rds_sg.id],
        skip_final_snapshot=True
        )

pulumi.export("url", api.url) 
