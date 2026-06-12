# -*- coding: utf-8 -*-
import sys; sys.path.insert(0, r'C:\Users\sagarwave\Downloads\comfyui_agent')
from config import LLM_MODEL, OPENCODE_ZEN_API_KEY, OPENCODE_ZEN_BASE_URL
from openai import OpenAI
import json
import os

print('Starting LLM test...', flush=True)

# Check env
print(f'API_KEY present: {bool(OPENCODE_ZEN_API_KEY)}', flush=True)
print(f'MODEL: {LLM_MODEL}', flush=True)
print(f'BASE_URL: {OPENCODE_ZEN_BASE_URL}', flush=True)

client = OpenAI(api_key=OPENCODE_ZEN_API_KEY, base_url=OPENCODE_ZEN_BASE_URL)

try:
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {'role': 'system', 'content': 'Say hello.'},
        ],
        temperature=0.1,
        max_tokens=50,
    )
    print(f'Response object: {response}', flush=True)
    print(f'Choices count: {len(response.choices)}', flush=True)
    print(f'Content: [{response.choices[0].message.content}]', flush=True)
    print(f'Finish reason: {response.choices[0].finish_reason}', flush=True)
except Exception as e:
    print(f'Error type: {type(e).__name__}', flush=True)
    print(f'Error: {e}', flush=True)
