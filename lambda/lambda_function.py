import json
import boto3
import datetime

def lambda_handler(event, context):
    # Parse incoming alert
    message = json.loads(event['Records'][0]['Sns']['Message'])
    
    print(f"Alert received: {message}")
    
    # Connect to Security Hub
    securityhub = boto3.client('securityhub', region_name='ap-northeast-2')
    
    # Get account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    
    # Map Falco priority to Security Hub severity
    severity_map = {
        'CRITICAL': 90,
        'ERROR': 70,
        'WARNING': 50,
        'NOTICE': 30,
        'INFO': 10
    }
    
    priority = message.get('priority', 'WARNING').upper()
    severity_score = severity_map.get(priority, 50)
    
    # Create Security Hub finding
    finding = {
        'SchemaVersion': '2018-10-08',
        'Id': f"falco-{context.aws_request_id}",
        'ProductArn': f"arn:aws:securityhub:ap-south-1:{account_id}:product/{account_id}/default",
        'GeneratorId': 'falco-runtime-security',
        'AwsAccountId': account_id,
        'Types': ['Software and Configuration Checks/Vulnerabilities'],
        'CreatedAt': datetime.datetime.utcnow().isoformat() + 'Z',
        'UpdatedAt': datetime.datetime.utcnow().isoformat() + 'Z',
        'Severity': {
            'Score': severity_score,
            'Label': priority
        },
        'Title': message.get('rule', 'Falco Security Alert'),
        'Description': message.get('output', 'Falco detected suspicious activity'),
        'Resources': [
            {
                'Type': 'Container',
                'Id': message.get('output_fields', {}).get('container.id', 'unknown'),
                'Details': {
                    'Other': {
                        'pod': message.get('output_fields', {}).get('k8s.pod.name', 'unknown'),
                        'namespace': message.get('output_fields', {}).get('k8s.ns.name', 'unknown'),
                        'rule': message.get('rule', 'unknown')
                    }
                }
            }
        ]
    }
    
    try:
        response = securityhub.batch_import_findings(Findings=[finding])
        print(f"Security Hub response: {response}")
        return {'statusCode': 200, 'body': 'Success'}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'body': str(e)}
