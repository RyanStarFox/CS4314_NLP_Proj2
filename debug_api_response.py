import os
import json
from dotenv import load_dotenv
import httpx
from openai import OpenAI

# Load env
load_dotenv(override=True)

api_key = os.getenv("VL_API_KEY") or os.getenv("OPENAI_API_KEY")
base_url = os.getenv("VL_API_BASE") or os.getenv("OPENAI_API_BASE")
model = os.getenv("VL_MODEL_NAME", "gpt-4o")

print(f"Testing Model: {model}")
print(f"Base URL: {base_url}")

# Manual client creation to ensure control
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    http_client=httpx.Client(verify=False)
)

sys_prompt = """
请输出一个JSON对象，包含一个字段 "text"，内容是李白的《静夜思》。
要求：
1. 必须是合法的JSON。
2. 保持诗歌的换行格式。
3. 不要包含Markdown代码块。
"""

print("\n--- Sending Request ---")
try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": "请输出。"}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    content = response.choices[0].message.content
    print("\n=== Raw Response Content (repr) ===")
    print(repr(content))
    print("\n=== Raw Response Content (print) ===")
    print(content)
    
    print("\n=== Attempting json.loads ===")
    try:
        parsed = json.loads(content)
        print("Success (Standard)!")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except json.JSONDecodeError as e:
        print(f"Standard json.loads failed: {e}")
        print("Trying strict=False...")
        try:
            parsed = json.loads(content, strict=False)
            print("Success (strict=False)!")
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except Exception as e2:
            print(f"Still failed: {e2}")

except Exception as e:
    import traceback
    print("\n=== Request Error ===")
    print(e)
    traceback.print_exc()
