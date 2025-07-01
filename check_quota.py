#!/usr/bin/env python3
"""Quick API quota check"""
from utils import get_openai_client

try:
    client = get_openai_client()
    response = client.chat.completions.create(
        model='gpt-4.1-nano',
        messages=[{'role': 'user', 'content': 'OK'}],
        max_tokens=5
    )
    print('✅ API QUOTA WORKING!')
except Exception as e:
    print('❌ API still blocked')