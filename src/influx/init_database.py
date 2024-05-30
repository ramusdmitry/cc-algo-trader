from influxdb_client import InfluxDBClient
from influxdb_client.client.buckets_api import BucketRetentionRules
import logging
import os

token = os.environ["INFLUX_TOKEN"]
org = "framework"
url = "http://localhost:13565"

client = InfluxDBClient(url=url, token=token, org=org)
buckets_api = client.buckets_api()

buckets = [
    {"name": "trading", "retention": 60*60*24*356},
    {"name": "news", "retention": 60*60*24*356},
]

for bucket in buckets:
    retention_rules = BucketRetentionRules(type="expire", every_seconds=bucket["retention"])
    buckets_api.create_bucket(bucket_name=bucket["name"], retention_rules=retention_rules, org=org)

logging.info("Database created")
client.close()
