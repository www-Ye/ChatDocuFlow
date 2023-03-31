import openai
import os
import time

class LLM_Operater:
    def __init__(self, openai_key, proxy="", model="gpt-3.5-turbo"):
        # Connect to the OpenAI API.
        if proxy != "":
            os.environ["http_proxy"] = proxy
            os.environ["https_proxy"] = proxy

        openai.api_key = openai_key

        self.model = model

    def conversation(self, messages):
        while True:
            try:
                completion = openai.ChatCompletion.create(
                    model=self.model, 
                    messages=messages
                    )
                break
            except Exception as e:
                print("An error occurred:", e.__class__.__name__)
                time.sleep(3)

        answer = completion["choices"][0]["message"]["content"]
        return answer
    
    def prompt_generation(self, prompt, sys_prompt=None):
        
        if sys_prompt is not None:
            messages = [{"role": "system", "content": sys_prompt},
                        {"role": "user", "content": prompt}]
        else:
            messages = [{"role": "user", "content": prompt}]

        while True:
            try:
                completion = openai.ChatCompletion.create(
                    model=self.model, 
                    messages=messages
                    )
                break
            except Exception as e:
                print("An error occurred:", e.__class__.__name__)
                time.sleep(3)

        res = completion["choices"][0]["message"]["content"]

        return res

    def get_embedding(self, text, model="text-embedding-ada-002"):
        text = text.replace("\n", " ")
        
        while True:
            try:
                emb = openai.Embedding.create(input = [text], model=model)['data'][0]['embedding']
                break
            except Exception as e:
                print("An error occurred:", e.__class__.__name__)
                time.sleep(3)

        return emb
    