

conda create -n "testing" python=3.11

conda activate testing

pip3 install -r requirements.txt

python3 -m uvicorn main:app --reload

http://127.0.0.1:8000/docs