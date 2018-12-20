import datetime
import json
import urllib.parse
import urllib.request
import boto3
import gzip

s3 = boto3.client('s3')
SLACK_CHANNEL = '#aws_cloudtrail'
HOOK_URL = 'https://hooks.slack.com/services/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'

def post_slack(message):
    request = urllib.request.Request(
        HOOK_URL,
        data=json.dumps(message).encode('utf-8'),
        method='POST',
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(request) as response:
        response_body = response.read().decode("utf-8")
    print(response_body)


def lambda_handler(event, context):
    #print(event['Records'])
    s3Info = json.loads(event['Records'][0]['Sns']['Message'])
    bucket = s3Info['s3Bucket']
    key = s3Info['s3ObjectKey'][0]

    try:
        obj = s3.download_file(bucket, key, '/tmp/json.gz')
        f = gzip.open('/tmp/json.gz', 'rb')
        content = f.read()
        f.close()
        jsonStr = str(content, 'utf-8')
        records = json.loads(jsonStr)['Records']
        
        messages = []
        for r in records:
            messages.append({
                "title": ":aws: CloudTrail",
                "value": "%s  (%s)" % (r["eventSource"], r["eventName"]),
                "short": False
            })
        
        message = {
            'username': 'CloudTrail',
            'channel': SLACK_CHANNEL,
            'icon_emoji': ':aws1:',
            'link_names': 1,
            'attachments': [{
                "fallback": "-",
                "color": "#cecdc8",
                "title": "Detail",
                "fields": messages,
                "ts":  datetime.datetime.utcnow().timestamp()
            }]
        }
        
        post_slack(message)
        return {}
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e

