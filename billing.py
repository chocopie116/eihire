from typing import cast, Any, Dict, List, Optional, NamedTuple

import datetime
import json
import urllib.request

import boto3

SLACK_CHANNEL = '#billing'
HOOK_URL = 'https://hooks.slack.com/services/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'

Metrics = Optional[List[Any]]


class Billing(NamedTuple):
    daily: float
    monthly: float

def get_session() -> Any:
    return boto3.session.Session()


def get_client() -> Any:
    session = get_session()
    return session.client(
        'cloudwatch',
        region_name='us-east-1',
    )


def list_metrics(client: Any) -> Metrics:
    metrics = client.list_metrics(
        Namespace='AWS/Billing',
        MetricName='EstimatedCharges',
    ).get('Metrics')
    return cast(Metrics, metrics)


def list_services(metrics: Metrics) -> List[str]:
    if metrics is None:
        return []
    dimensions = [_list_to_dict(x['Dimensions']) for x in metrics]
    return [x['ServiceName'] for x in dimensions if 'ServiceName' in x]


def _list_to_dict(src: List[Dict[str, Any]]) -> Dict[str, Any]:
    res = {}
    for x in src:
        res[x['Name']] = x['Value']
    return res


def calc_total_billing(client: Any, dt: datetime.datetime) -> Billing:
    return _calc_billings(_get_billings(client, dt))


def calc_service_billing(client: Any, dt: datetime.datetime, service: str) -> Billing:
    return _calc_billings(_get_billings(client, dt, service))


def _get_billings(client: Any, dt: datetime.datetime, service_name: Optional[str]=None) -> List[Any]:
    dimensions = [{'Name': 'Currency', 'Value': 'USD'}]
    if service_name is not None:
        dimensions.append({'Name': 'ServiceName', 'Value': service_name})

    items = client.get_metric_statistics(
        Namespace='AWS/Billing',
        MetricName='EstimatedCharges',
        Dimensions=dimensions,
        StartTime=dt - datetime.timedelta(days=2),
        EndTime=dt,
        Period=86400,
        Statistics=['Maximum']
    )['Datapoints']
    return [x for x in items if x['Timestamp'].month == dt.month]


def _calc_billings(items: list) -> Billing:
    if len(items) == 1:
        # the first day of month
        price = items[0]['Maximum']
        return Billing(price, price)
    return Billing(
        daily=abs(items[0]['Maximum'] - items[1]['Maximum']),
        monthly=max([x['Maximum'] for x in items])
    )


def post_slack(message: Dict[str, str]) -> None:
    request = urllib.request.Request(
        HOOK_URL,
        data=json.dumps(message).encode('utf-8'),
        method='POST',
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(request) as response:
        response_body = response.read().decode("utf-8")
    print(response_body)


def format_price(caption: str, billing: Billing) -> str:
    return '%s: $%.2f ($%.2f)' % (caption, billing.daily, billing.monthly)


def lambda_handler(event: dict, context: Any) -> None:
    today = datetime.datetime.utcnow()

    client = get_client()

    total = calc_total_billing(client, today)

    services = list_services(list_metrics(client))
    billings = [(x, calc_service_billing(client, today, x))
                for x in services]

    lines = [
        '%s daily (monthly)' % today.strftime('%Y-%m-%d'),
        format_price('Total', total),
    ]
    for x in billings:
        lines.append('- %s' % format_price(*x))

    summary = {
	    "fallback": "Required plain-text summary of the attachment.",
	    "color": "#36a64f",
	    "title": "Summary",
	    "fields": [
		{
		    "title": ":moneybag: ALL",
		    "value": "$%.2f (+ $%.2f)" % (total.monthly, total.daily),
		    "short": False
		    },
		],
	    "ts": today.timestamp()
	    }

    detail = {
	    "fallback": "Required plain-text summary of the attachment.",
	    "color": "warning",
	    "title": "Detail",
	    "fields": [
		{
		    "title": ":aws: EC2",
		    "value": "$0.02 +($0.00)",
		    "short": True
		    },
		{
		    "title": ":aws: EC2",
		    "value": "$0.02 +($0.00)",
		    "short": True
		    },
		],
	    "ts": today.timestamp()
	    }

    message = {
	    'username': 'AWS Billing at %s' % today.strftime('%Y-%m-%d'),
	    'channel': SLACK_CHANNEL,
	    'icon_emoji': ':aws1:',
	    'link_names': 1,
	    "attachments": [ summary, detail]
	    }

    post_slack(message)

if __name__ == '__main__':
    lambda_handler({}, {})
