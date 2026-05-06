"""Probe what the local mlx server actually returns for gpt-oss-20b."""
import json, re
from pathlib import Path
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[3]
api_key = re.search(r'^\s*LOCAL_API_KEY\s*=\s*"?([^"]+)"?', (ROOT/".env").read_text(), re.M).group(1)
client = OpenAI(api_key=api_key, base_url="http://127.0.0.1:8000/v1")

prompt_path = ROOT / "spp" / "hair-loss-relevance" / "runs" / "gpt-oss-20b-MXFP4-Q8" / "run_01" / "prompt_v01.md"
prompt = prompt_path.read_text()

resp = client.chat.completions.create(
    model="gpt-oss-20b-MXFP4-Q8",
    messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": "<input_row>\nI'm 24 and on fin for 6 months. Crown is fuller, temples slow.\n</input_row>"},
    ],
    temperature=0.0, max_tokens=400,
)
print("--- choices[0].message ---")
msg = resp.choices[0].message
print(f"content: {msg.content!r}")
for attr in ("reasoning_content", "reasoning", "tool_calls", "function_call"):
    if hasattr(msg, attr):
        print(f"{attr}: {getattr(msg, attr)!r}")
print("--- model_dump ---")
print(json.dumps(resp.model_dump(), indent=2, default=str)[:3000])
