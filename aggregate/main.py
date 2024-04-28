import os
import json
from datetime import date, datetime
import uuid
from typing import List

from fastapi import FastAPI
from openai import OpenAI

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.models.errors import SDKError
from sse_starlette.sse import EventSourceResponse

from fastapi.middleware.cors import CORSMiddleware

from data_model import Order
from utils import create

directory_path = 'receipts'
un_client = UnstructuredClient(api_key_auth=os.getenv('UNSTRUCTURED_IO_API'))
client = OpenAI()
app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


def process_streamer():
    total = 0

    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)

        if os.path.isfile(file_path) and filename.lower().endswith('.pdf'):
            total += 1

    for index, filename in enumerate(os.listdir(directory_path)):
        file_path = os.path.join(directory_path, filename)

        if os.path.isfile(file_path) and filename.lower().endswith('.pdf'):
            yield {
                "event": "status",
                "id": uuid.uuid4(),
                "retry": 1500,
                "data": {"index": index, "total": total}
            }

            file = open(file_path, "rb")
            req = shared.PartitionParameters(
                files=shared.Files(
                    content=file.read(),
                    file_name=file_path,
                ),
                strategy="ocr_only",
                languages=["swe"],
            )

            try:
                res = un_client.general.partition(req)
                concat_elements = " ".join(e["text"] for e in res.elements)

            except SDKError as e:
                print(e)

            raw_order = concat_elements

            prompt = f"""
            Given the following order with items bough from a grocery store Willys, 
            please extract a dictornary that contains information about the order.

            Please respond ONLY with valid json that conforms to this pydantic json_schema: {Order.schema_json()}. Do not include additional text other than the object json as we will load this object with json.loads() and pydantic.
            """

            messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": raw_order},       
            ]

            order = create(
                client=client,
                messages=messages, 
                model_class=Order, 
                model="gpt-3.5-turbo-0125",
                max_tokens=4096,
                response_format={ "type": "json_object" }
            )

            order = order.dict()
            order["uuid"] = str(uuid.uuid4())

            json_content = json.dumps(order, default=json_serial, ensure_ascii=False)

            yield {
                "event": "order",
                "id": uuid.uuid4(),
                "retry": 1500,
                "data": json_content
            }


@app.get("/process_stream")
def process():
    return EventSourceResponse(process_streamer())
