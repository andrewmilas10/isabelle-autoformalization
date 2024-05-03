# https://github.com/wellecks/ntptutorial/blob/main/partII_dsp/dsp_utils.py

import time
import os
import openai


class LMFunction(object):
    def __init__(self, engine='gpt-3.5-turbo', max_tokens=512):
        self.engine = engine
        self.max_tokens = max_tokens
        self.openai = openai
        openai.api_key = os.environ['OPENAI_API_KEY']

    def _call_api(self, prompt, engine, max_tokens, max_retries=10, retry_wait=2):
        for i in range(max_retries):
            try:
                return self.openai.ChatCompletion.create(
                    model=engine,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=1.0
                )
            except self.openai.error.OpenAIError as e:
                time.sleep(retry_wait)
        return {'choices': [{'message': {'content': ''}}]}

    def _parse_message(self, msg):
        try:
            content = msg['choices'][0]['message']['content']
        except (IndexError, KeyError):
            content = ''
        return content

    def f(self, prompt, x):
        msg = self._call_api(
            prompt=prompt+x,
            engine=self.engine,
            max_tokens=self.max_tokens
        )
        evaluation = self._parse_message(msg)
        return evaluation

# def get