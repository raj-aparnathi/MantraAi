import requests, config

key = config.GEMINI_API_KEY
url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + key

payload = {
    'system_instruction': {'parts': [{'text': config.PERSONA_SYSTEM_PROMPT}]},
    'contents': [{'role': 'user', 'parts': [{'text': 'Say hello in one sentence as Mantra.'}]}],
    'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 100}
}

print('Testing gemini-2.5-flash with your API key...')
try:
    r = requests.post(url, json=payload, timeout=15)
    print('HTTP status:', r.status_code)
    if r.status_code == 200:
        reply = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        print('Gemini replied:', reply)
        print()
        print('SUCCESS! Gemini is fully working.')
    else:
        err = r.json().get('error', {})
        print('Error:', err.get('code'), '-', err.get('message','')[:200])
except Exception as e:
    print('Error:', e)
