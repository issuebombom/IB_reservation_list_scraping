import json

# env 파일 불러오기
with open("./.env.json", "r") as f:
    ENV = json.load(f)
