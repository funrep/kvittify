import os
import json
from datetime import date, datetime
import uuid
from typing import List

from fastapi import FastAPI
from fastapi.responses import Response

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

db = {}

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
                "data": json.dumps({"index": index, "total": total})
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
            order["file_path"] = file_path

            db[order["uuid"]] = order

            json_content = json.dumps(order, default=json_serial, ensure_ascii=False)

            print(json.dumps(order, default=json_serial, ensure_ascii=False, indent=4))

            yield {
                "event": "order",
                "id": uuid.uuid4(),
                "retry": 1500,
                "data": json_content
            }


def test_streamer():
    order = {
        "items": [
            {
                "product": "PÅSKMUST 1.4L",
                "price": 9.49,
                "food_type": "Beverage",
                "discount": None,
                "quantity": 2,
                "quantity_kg": None,
                "price_per_kg": None
            },
            {
                "product": "RAMLÖSA FLÄDER/LIME",
                "price": 9.9,
                "food_type": "Beverage",
                "discount": None,
                "quantity": 1,
                "quantity_kg": None,
                "price_per_kg": None
            },
            {
                "product": "MARGARIN M/FR 7096",
                "price": 19.9,
                "food_type": "Dairy",
                "discount": None,
                "quantity": 1,
                "quantity_kg": None,
                "price_per_kg": None
            }
        ],
        "date": "2024-04-19",
        "uuid": "92c1424d-52a9-45ef-b0c3-d6c86e3d06e3",
        "file_path": "receipts/2024-04-19T19_29_21.pdf"
    } 

    db["92c1424d-52a9-45ef-b0c3-d6c86e3d06e3"] = order

    json_content = json.dumps(order, default=json_serial, ensure_ascii=False)

    yield {
        "event": "status",
        "id": uuid.uuid4(),
        "retry": 1500,
        "data": json.dumps({"index": 0, "total": 1})
    }

    yield {
        "event": "order",
        "id": uuid.uuid4(),
        "retry": 1500,
        "data": json_content
    }
     
@app.get("/test_stream")
def process():
    return EventSourceResponse(test_streamer())


@app.get("/process_stream")
def process():
    return EventSourceResponse(process_streamer())

@app.get("/get_receipt")
def download_receipt(uuid: str):
    headers = {f'Content-Disposition': 'inline; filename="{uuid}.pdf"'}

    if uuid not in db.keys():
        return Response(status_code=404, content="File not found in db")
    
    file_path = db[uuid]["file_path"]

   # Ensure the file exists before attempting to open it
    if not os.path.isfile(file_path):
        return Response(status_code=404, content="File not found in file system")

    # Read the binary content of the file
    with open(file_path, 'rb') as file:
        file_content = file.read()

    return Response(content=file_content, headers=headers, media_type='application/pdf')

