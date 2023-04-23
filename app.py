# app.py
from flask import Flask, request, jsonify
from flask import render_template
import time
import numpy as np
from doc_management import Doc_Management
import argparse
# from flask_cors import CORS

app = Flask(__name__)
# CORS(app)

sys_qa_prompt = "You are a professional researcher, please answer my questions based on the context and your own thoughts."
sys_message = [{"role": "system", "content": sys_qa_prompt}]

messages = []
messages_context = []

def answer_generator(question):
    global messages, messages_context, sys_qa_prompt, sys_message

    print(question)
    if question == '重置':
        yield '重置成功'
    else:
        messages = messages[-6:]
        messages_context = messages_context[-6:]

        question_context = '\n'.join(messages_context) + '\n' + question
        # print(question_context)
        question_emb = np.array(DM.llm_op.get_embedding(question_context)).astype('float32').reshape(1, -1)
        # print(question_emb)

        threshold = 0.2
        filtered_indices = []
        k = len(DM.id2chunk)
        while (len(filtered_indices) == 0) and (threshold <= DM.chunk_range_distance + 0.2):
            D, I = DM.chunk_index.search(question_emb, k)
            D, I = D[0], I[0]
            filtered_indices = I[D < threshold]
            filtered_distances = D[D < threshold]
            threshold += 0.05

        contexts = []
        sources_info_dict = {}
        if len(filtered_indices) > 0:
            for i, idx in enumerate(filtered_indices):
                tmp = DM.id2chunk[str(idx)]
                source = tmp['source']
                source_gen_title = tmp['source_gen_title']
                source_summary = tmp['source_summary']
                page_span = tmp['page_span']
                chunk_id = tmp['chunk_id']
                source_s_tags = tmp['semantic_tags']
                source_r_tags = tmp['regular_tags']
                chunk_text = tmp['chunk_text']
                source_info = f'source: {source}\nsource_gen_title:{source_gen_title}\nsource_summary: {source_summary}\nsemantic_tags: {source_s_tags}\nregular_tags: {source_r_tags}'
                if source_info not in sources_info_dict:
                    sources_info_dict[source_info] = {'pages': page_span.split(','), 'chunks': set([chunk_id])}
                else:
                    sources_info_dict[source_info]['pages'].extend(page_span.split(','))
                    sources_info_dict[source_info]['chunks'].add(chunk_id)
                prompt_text = f'page_span: {page_span}\nchunk_id: {chunk_id}]\nchunk_text: {chunk_text}'
                contexts.append(f'source: {source}\n' + prompt_text)
        related_doc = ''
        for key, v in sources_info_dict.items():
            # print(key)
            related_doc = key + '\n'
            pages_list = sorted(list(set(v['pages'])), key=int)
            chunks_list = sorted(list(set(v['chunks'])), key=int)
            # print(pages_list, chunks_list)
            # print('pages:{}\nchunks:{}'.format(','.join(pages_list), ','.join(chunks_list)))
            related_doc += 'pages:{}\nchunks:{}'.format(','.join(pages_list), ','.join(chunks_list))
            print(related_doc)
            yield related_doc
            # related_doc += '=' * 50 + '\n'
        yield '=' * 20 + 'span nums: {}\n'.format(len(contexts)) + '=' * 20
        # print(related_doc)
        # yield related_doc

        if len(contexts) > 0:
            tmp_messages = sys_message + messages
            prompt = 'paragraphs:[{}]\nBased on the context, Answer the question in {}. Q:' + question
            new_spans = contexts
            print('span nums:', len(new_spans))
            flag = True
            while flag or (len(new_spans) > 1):
                tmp_ans = ''
                flag = False
                old_spans = new_spans
                sum_span_tokens = 0
                for span in old_spans:
                    span_tokens = DM.tokenizer.encode(span)
                    sum_span_tokens += len(span_tokens)
                avg_span_tokens_nums = 1. * sum_span_tokens / len(old_spans)
                span = int(3072. / avg_span_tokens_nums)
                span_overlap = int(span * 0.2)
                print(f'span:{span}  span_overlap:{span_overlap}')
                start = 0
                add_span = span - span_overlap
                new_spans = []
                while start < len(old_spans):
                    if tmp_messages is not None:
                        new_span = DM.llm_op.conversation(tmp_messages + [{"role": "user", "content": prompt.format('\n'.join(old_spans[start:start+span]), DM.language)}])
                    else:
                        new_span = DM.llm_op.prompt_generation(prompt.format(' '.join(old_spans[start:start+span]), DM.language))
                    new_spans.append(new_span)
                    yield new_span
                    start += add_span

                    # print(new_span)

                print('span nums:',len(new_spans))
                yield '=' * 20 + 'span nums: {}\n'.format(len(new_spans)) + '=' * 20
                
            ans = new_spans[0]
        else:
            ans = DM.llm_op.prompt_generation(f'Answer question in {DM.language}. Q:{question}')
            yield ans

        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": ans})
        messages_context.append(question)
        messages_context.append(ans)
        
        # 模拟一个逐步产生回答的过程
        # yield "第一个回答"
        # time.sleep(2)
        # yield "第二个回答"
        # # time.sleep(3)
        # yield "第三个回答"

@app.route('/ask', methods=['POST'])
def ask():
    question = request.form.get('question')
    try:
        answer = next(answers_map[question])
    except StopIteration:
        answer = None
        del answers_map[question]
    return jsonify(answer=answer)

@app.route('/start', methods=['POST'])
def start():
    question = request.form.get('question')
    answers_map[question] = answer_generator(question)
    return jsonify()

answers_map = {}

# 在 app.py 中添加以下代码
@app.route('/')
def index():
    return render_template('index.html')

parser = argparse.ArgumentParser()

parser.add_argument("--doc_dir", default="docs", type=str)
parser.add_argument("--db_name", default="docuflow.db", type=str)
parser.add_argument("--language", default="Chinese", type=str)
parser.add_argument("--doc_range_distance", default=0.4, type=float, help="The doc retrieval threshold returns higher similarity for closer distances.")
parser.add_argument("--chunk_range_distance", default=0.3, type=float, help="The chunk retrieval threshold returns higher similarity for closer distances.")
parser.add_argument("--system", default="windows", type=str, help="windows/mac")

parser.add_argument("--openai_key", default="", type=str)
parser.add_argument("--proxy", default="", type=str)

args = parser.parse_args()

print('*Welcome to Document Management*')
# print(asd)
DM = Doc_Management(args)

if __name__ == '__main__':
    # app.run(debug=True)
    app.run()
