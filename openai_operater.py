import openai
import os
import time

class Openai_Operater:
    def __init__(self, openai_key, proxy=""):
        # Connect to the OpenAI API.
        if proxy != "":
            os.environ["http_proxy"] = proxy
            os.environ["https_proxy"] = proxy

        openai.api_key = openai_key

    def conversation(self, messages):
        while True:
            try:
                completion = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo", 
                    messages=messages
                    )
                break
            except Exception as e:
                print("An error occurred:", e.__class__.__name__)
                time.sleep(3)

        answer = completion["choices"][0]["message"]["content"]
        return answer
    
    def get_gpt_res(self, prompt):
        
        while True:
            try:
                completion = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo", 
                    messages=[{"role": "user", "content": prompt}]
                    )
                break
            except Exception as e:
                print("An error occurred:", e.__class__.__name__)
                time.sleep(3)

        res = completion["choices"][0]["message"]["content"]
        # print(summary)

        return res
    
    def summary_para(self, text, language='Chinese'):
        # Summarize the document.

        while True:
            try:
                completion = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo", 
                    messages=[{"role": "user", "content": "{}\nSummarize this paragraph in {}:".format(text, language)}]
                    )
                break
            except Exception as e:
                print("An error occurred:", e.__class__.__name__)
                time.sleep(3)

        summary = completion["choices"][0]["message"]["content"]
        # print(summary)

        return summary

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
    