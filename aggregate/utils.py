import json
from typing import List

from pydantic import BaseModel, ValidationError

def create(client, messages : List[dict], model_class: BaseModel, retry=5, temperature=0, **kwargs) -> BaseModel:
    last_exception = None
    for i in range(retry+1):
        response = client.chat.completions.create(
            messages=messages, 
            temperature=temperature, 
            **kwargs
        )

        print(response.choices[0].message)

        assistant_message = response.choices[0].message.content
        content = assistant_message

        try:
            json_content = json.loads(content)
        except Exception as e:
            last_exception = e
            error_msg = f"json.loads exception: {e}"
            print(error_msg)
            messages.append(assistant_message)
            messages.append({"role"   : "system",
                            "content": error_msg})
            continue
        try:
            return model_class(**json_content)
        except ValidationError as e:
            last_exception = e
            error_msg = f"pydantic exception: {e}"
            print(error_msg)
            messages.append(assistant_message)            
            messages.append({"role"   : "system",
                            "content": error_msg})    
    raise last_exception