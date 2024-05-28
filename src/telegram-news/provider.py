from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import asyncio
import os
from parser import TelegramNewsParser
from influxdb_client import InfluxDBClient
import uvicorn


app = FastAPI()
news_parser = TelegramNewsParser()
influxdb_token = os.environ["INFLUX_TOKEN"]
org = 'framework'
bucket = 'news'
url = 'http://localhost:13565'

query_api = InfluxDBClient(url=url, token=influxdb_token, org=org).query_api()

class NewsRequest(BaseModel):1
    pair: str
    take: int = 100
    skip: int = 0

@app.get("/{pair}/latest/")
async def get_latest_news(pair: str, take: int = 100, skip: int = 0):
    try:
        await news_parser.get_news(pair, limit=take, offset=skip)
        query = f'''
        from(bucket: "{bucket}")
        |> range(start: -30d)
        |> filter(fn: (r) => r["_measurement"] == "news")
        |> filter(fn: (r) => r["channel"] == "{pair}")
        |> sort(columns: ["_time"], desc: true)
        |> limit(n: {take})
        |> offset(n: {skip})
        '''
        result = query_api.query(org=org, query=query)
        news = []
        for table in result:
            for record in table.records:
                news.append({
                    "id": record.get_value(),
                    "channel": record.values["channel"],
                    "date": record.get_time().strftime('%Y-%m-%d %H:%M:%S'),
                    "message": record.values["message"]
                })
        return news
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
