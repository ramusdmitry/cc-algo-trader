import os
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import asyncio
from datetime import datetime

api_id = os.environ["TG_API_ID"]
api_hash = os.environ["TG_API_HASH"]
phone = os.environ["TG_PHONE"]
channel_ids = os.environ["TG_CHANNELS"]
influxdb_token = os.environ["INFLUX_TOKEN"]
org = 'framework'
bucket = 'news'
url = 'http://localhost:13565'

class TelegramNewsParser:
    def __init__(self):
        self.client = TelegramClient(phone, api_id, api_hash)
        self.client.connect()
        if not self.client.is_user_authorized():
            self.client.send_code_request(phone)
            self.client.sign_in(phone, input('Enter the code: '))
        self.influxdb_client = InfluxDBClient(url=url, token=influxdb_token, org=org)
        self.write_api = self.influxdb_client.write_api(write_options=SYNCHRONOUS)

    async def fetch_news(self, channel_username, limit=100, offset=0):
        channel = await self.client.get_entity(PeerChannel(channel_username))
        history = await self.client(GetHistoryRequest(
            peer=channel,
            limit=limit,
            offset_date=None,
            offset_id=offset,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0
        ))
        messages = history.messages
        news_list = []
        for message in messages:
            news_list.append({
                'id': message.id,
                'channel': channel_username,
                'date': message.date,
                'message': message.message
            })
        return news_list

    def save_news(self, news_list):
        for news in news_list:
            point = Point("news") \
                .tag("channel", news['channel']) \
                .field("id", news['id']) \
                .field("message", news['message']) \
                .time(news['date'])
            self.write_api.write(bucket=bucket, org=org, record=point)

    async def get_news(self, channel_username=channel_ids, limit=100, offset=0):
        news_list = await self.fetch_news(channel_username, limit, offset)
        self.save_news(news_list)
        return news_list
    
    async def run(self):
        await self.get_news()


if __name__ == "__main__":
    parser = TelegramNewsParser()
    loop = asyncio.get_event_loop()
    loop.run_forever(parser.run())