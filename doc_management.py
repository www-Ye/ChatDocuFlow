from db_operater import Sqlite_DB
from llm_operater import LLM_Operater
import numpy as np
import win32api
import pickle
import faiss
import json
import os
import fitz
import re
import tiktoken

Action_Help_EN = '''Choose your action:

1. Document search - Retrieve relevant documents based on query and tags.
2. Chunk-level conversation - Retrieve answers to questions based on relevant pages.
3. Add/update semantic tags - Automatically associate similar documents with tags. (To be added.)
4. Update documents - Update PDF files in the system's folder (automatically done each time the system is started).
Press Enter to exit the system.'''

Action_Help_ZH = '''选择你的操作：

1. 文档搜索 - 根据query、tag选择检索相关文档
2. 块级问答 - 根据问题检索相关页面回答问题
3. 添加/更新语义标签 - 自动将相似文档与标签进行关联 (To be added.)
4. 更新文档 - 将文件夹中的pdf更新至系统（每次启动系统会自动更新）
输入回车键退出系统。'''

Doc_Help_EN = '''The query should be entered in the following format:

query=[] has_s_tag=[] no_s_tag=[] has_r_tag=[] no_r_tag=[]

All sections cannot be omitted at the same time. Multiple tags can be separated by commas within [].

* "query=[]" specifies the search query you want to perform.
* "has_s_tag=[]" specifies the list of semantic tags that the document should have. (To be added.)
* "no_s_tag=[]" specifies the list of semantic tags that the document should not have. (To be added.)
* "has_r_tag=[]" specifies the list of regular tags that the document should have. (To be added.)
* "no_r_tag=[]" specifies the list of regular tags that the document should not have. (To be added.)
Press Enter to go back to the previous level.'''

Doc_Help_ZH = '''查询应以以下格式输入：

query=[] has_s_tag=[] no_s_tag=[] has_r_tag=[] no_r_tag=[]

所有部分项不能同时省略。多个标签可以用逗号在[]中分隔。

* "query=[]" 指定您想执行的搜索查询。
* "has_s_tag=[]" 指定文档应具有的语义标签列表。 (To be added.)
* "no_s_tag=[]" 指定文档不应具有的语义标签列表。 (To be added.)
* "has_r_tag=[]" 指定文档应具有的普通标签列表。 (To be added.)
* "no_r_tag=[]" 指定文档不应具有的普通标签列表。 (To be added.)
按 Enter 返回上一级。'''

Add_Tags_Help_EN = '''Manually add semantic tags, multiple tags can be separated by commas, and the specific format is as follows:
* "add_tag=[xxx,yyy|similar,zzz]" means adding tags, where |similar indicates adding documents that are semantically similar to the tag.
* "del_tag=[xxx,yyy]" means deleting tags.

Press Enter to return.'''

Add_Tags_Help_ZH = '''添加标签，多个标签可以用逗号分隔，具体格式如下：

* "add_s_tag=[xxx,yyy]" 添加语义标签，当新标签首次创建时会自动添加与该标签语义相似的文档。
* "del_s_tag=[xxx,yyy]" 删除该文档的语义标签。
* "add_r_tag=[xxx,yyy]" 添加普通标签
* "del_r_tag=[xxx,yyy]" 删除普通标签
按 Enter 返回。'''

Doc_Op_Help_EN = '''Please select your action:

1. Open the document and enter conversation mode
2. Open the document
3. Show document chunk details
4. Enter conversation mode
5. Add/remove semantic tags (To be added.)
6. Add/remove regular tags (To be added.)
Press Enter to return.'''

Doc_Op_Help_ZH = '''请选择您的操作：

1. 打开文档并进入对话模式
2. 打开文档
3. 展示文档chunk详细信息
4. 进入对话模式
5. 添加/删除语义标签 (To be added.)
6. 添加/删除普通标签 (To be added.)
按 Enter 返回。'''

class Doc_Management:
    def __init__(self, args):
        self.doc_dir = args.doc_dir
        self.language = args.language
        self.delimiter = '=' * 50
        
        self.db = Sqlite_DB(args.db_name)

        self.llm_op = LLM_Operater(args.openai_key, args.proxy)

        self.query_pattern = re.compile(r'query=\[(.*?)\]')
        self.semantic_tag_pattern = re.compile(r'has_s_tag=\[(.*?)\]')
        self.no_semantic_tag_pattern = re.compile(r'no_s_tag=\[(.*?)\]')
        self.regular_tag_pattern = re.compile(r'has_r_tag=\[(.*?)\]')
        self.no_regular_tag_pattern = re.compile(r'no_r_tag=\[(.*?)\]')

        self.emb_size = 1536
        self.doc_range_distance = args.doc_range_distance
        self.chunk_range_distance = args.chunk_range_distance

        self.db.open()
        doc_list = self.db.search("docs_table", selected_columns=["source"])
        semantic_tags_result = self.db.search("semantic_tags_table", selected_columns=["tag", "embedding"])
        regular_tags_result = self.db.search("regular_tags_table", selected_columns=["tag"])
        self.db.close()

        self.regular_tags_list = [t[0] for t in regular_tags_result]
        self.doc_list = [d[0] for d in doc_list]
        # print(self.doc_list)

        self.tag_index = None
        self.semantic_tags_list = []
        if len(semantic_tags_result) > 0:
            self.semantic_tags_list, self.tag_embeddings = zip(*semantic_tags_result)
            self.semantic_tags_list = list(self.semantic_tags_list)
            self.tag_embeddings = np.array(list(self.tag_embeddings)).astype('float32')

            self.tag_index = faiss.IndexFlatL2(self.tag_embeddings)

        # print(self.semantic_tags_list)
        # print(self.doc_list)

        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self.update_doc()

        if (args.language == 'Chinese') or (args.language == 'chinese'):
            self.action_help = Action_Help_ZH
            self.doc_search_help = Doc_Help_ZH
            self.add_tags_help = Add_Tags_Help_ZH
            self.doc_op_help = Doc_Op_Help_ZH
        else:
            self.action_help = Action_Help_EN
            self.doc_search_help = Doc_Help_EN
            self.add_tags_help = Add_Tags_Help_EN
            self.doc_op_help = Doc_Op_Help_EN

    def update_doc(self):
        file_list = os.listdir(self.doc_dir)
        tmp_diff = set(file_list) - set(self.doc_list)
        add_list = list(tmp_diff)
        tmp_diff = set(self.doc_list) - set(file_list)
        del_list = list(tmp_diff)
        self.doc_nums = len(self.doc_list)
        # add_list = file_list

        add_nums = 0
        for item in add_list:
            if(item.endswith('.pdf')):
                print('Add {} to the DB'.format(item))
                pages_list = self.parse_pdf(os.path.join(self.doc_dir, item))
                self.add_doc(item, pages_list)
                add_nums += 1

        del_nums = 0
        for item in del_list:
            print('Delete {} from the DB'.format(item))
            self.del_doc(item)

            del_nums += 1

        self.doc_nums = self.doc_nums + add_nums - del_nums

        print('add nums:', add_nums)
        print('del nums:', del_nums)
        print('doc nums:', self.doc_nums)

        # self.update_embs()

        if (len(add_list) > 0) or (len(del_list) > 0):
            self.update_embs()
        else:
            with open('cache/id2doc.json', 'r', encoding='utf-8') as f:
                self.id2doc = json.load(f)
            with open('cache/doc2id.json', 'r', encoding='utf-8') as f:
                self.doc2id = json.load(f)
            self.doc_index = faiss.read_index("cache/doc_index.faiss")

            with open('cache/id2chunk.json', 'r', encoding='utf-8') as f:
                self.id2chunk = json.load(f)
            with open('cache/chunk2id.json', 'r', encoding='utf-8') as f:
                self.chunk2id = json.load(f)
            self.chunk_index = faiss.read_index("cache/chunk_index.faiss")

        self.db.open()
        doc_list = self.db.search("docs_table", selected_columns=["source"])
        self.db.close()

        self.doc_list = [d[0] for d in doc_list]

        # return file_nums
    
    def update_embs(self):

        # embedding doc
        self.db.open()
        doc_infos = self.db.search("docs_table")
        self.id2doc = {}
        self.doc2id = {}
        doc_embs = []
        for i, doc in enumerate(doc_infos):
            source = doc[0]
            summary = doc[1]
            page_nums = doc[2]
            chunk_nums = doc[3]
            source_emb = doc[4]
            s_tags = self.db.search("semantic_tags2source_table", conditions={"source": source}, selected_columns=["tag"])
            s_tags = [t[0] for t in s_tags]
            r_tags = self.db.search("regular_tags2source_table", conditions={"source": source}, selected_columns=["tag"])
            r_tags = [t[0] for t in r_tags]
            self.id2doc[str(i)] = {'source': source, 'summary': summary, 'page_nums': page_nums, 'chunk_nums': chunk_nums, \
                                   'semantic_tags': ','.join(s_tags), 'regular_tags': ','.join(r_tags)}
            self.doc2id[source] = i
            s_tag_embs = []
            for tag in s_tags:
                s_tag_emb = pickle.loads(self.db.search("semantic_tags_table", conditions={"tag": tag}, selected_columns=["embedding"])[0])
                s_tag_embs.append(s_tag_emb)
            r_tag_embs = []
            for tag in r_tags:
                r_tag_emb = pickle.loads(self.db.search("regular_tags_table", conditions={"tag": tag}, selected_columns=["embedding"])[0])
                r_tag_embs.append(r_tag_emb)
            source_emb = [pickle.loads(source_emb)]
            embs = source_emb + s_tag_embs + r_tag_embs
            embs = list(np.mean(np.array(embs), axis=0))
            doc_embs.append(embs)
        self.db.close()
        with open('cache/id2doc.json', 'w', encoding='utf-8') as f:
            json.dump(self.id2doc, f)
        with open('cache/doc2id.json', 'w', encoding='utf-8') as f:
            json.dump(self.doc2id, f)
        if len(doc_embs) > 0:
            doc_embs = np.array(doc_embs).astype('float32')
            self.doc_index = faiss.IndexFlatL2(self.emb_size)
            self.doc_index.add(doc_embs)
            faiss.write_index(self.doc_index, "cache/doc_index.faiss")

        # embedding chunk
        self.db.open()
        chunks_infos = self.db.search("chunks_table")
        self.id2chunk = {}
        self.chunk2id = {}
        chunk_embs = []
        for i, chunk in enumerate(chunks_infos):
            source = chunk[0]
            page_span = chunk[1]
            chunk_id = chunk[2]
            chunk_text = chunk[3]
            chunk_summary = chunk[4]
            # print(source)
            # print(self.db.search("docs_table", conditions={"source": source}))
            source_info = self.db.search("docs_table", conditions={"source": source})[0]
            s_tags = self.db.search("semantic_tags2source_table", conditions={"source": source}, selected_columns=["tag"])
            s_tags = [t[0] for t in s_tags]
            r_tags = self.db.search("regular_tags2source_table", conditions={"source": source}, selected_columns=["tag"])
            r_tags = [t[0] for t in r_tags]
            self.id2chunk[str(i)] = {'source': source, 'source_summary': source_info[1], 'source_page_nums': source_info[2], 'source_chunk_nums': source_info[3], \
                                     'semantic_tags': ','.join(s_tags), 'regular_tags': ','.join(r_tags), \
                                    'page_span': page_span, 'chunk_id': chunk_id, 'chunk_text': chunk_text, 'chunk_summary': chunk_summary}
            self.chunk2id[f"{source} {page_span} {chunk_id}"] = i
            chunk_emb = [pickle.loads(chunk[-1])]
            source_emb = [pickle.loads(source_info[-1])]
            s_tag_embs = []
            for tag in s_tags:
                s_tag_emb = pickle.loads(self.db.search("semantic_tags_table", conditions={"tag": tag}, selected_columns=["embedding"])[0])
                s_tag_embs.append(s_tag_emb)
            r_tag_embs = []
            for tag in r_tags:
                r_tag_emb = pickle.loads(self.db.search("regular_tags_table", conditions={"tag": tag}, selected_columns=["embedding"])[0])
                r_tag_embs.append(r_tag_emb)
            embs = source_emb + chunk_emb + s_tag_embs + r_tag_embs
            # print(len(embs))
            embs = list(np.mean(np.array(embs), axis=0))
            chunk_embs.append(embs)
        self.db.close()
        with open('cache/id2chunk.json', 'w', encoding='utf-8') as f:
            json.dump(self.id2chunk, f)
        with open('cache/chunk2id.json', 'w', encoding='utf-8') as f:
            json.dump(self.chunk2id, f)
        if len(chunk_embs) > 0:
            chunk_embs = np.array(chunk_embs).astype('float32')
            self.chunk_index = faiss.IndexFlatL2(self.emb_size)
            self.chunk_index.add(chunk_embs)
            faiss.write_index(self.chunk_index, "cache/chunk_index.faiss")

    def parse_pdf(self, path):

        item_pdf = fitz.open(path) # pdf document
        pages_list = [page.get_text().replace('\n', ' ') for page in item_pdf]

        return pages_list
    
    def search_doc(self, op, search_type='doc'):
        res, res_text = self.semantic_search(op)

        while (len(res) > 0):

            print('\n'.join(res_text))
            print('Number of search results:', len(res))

            print('Open the document corresponding to the input ID. Press enter to go back.')
            op = input()

            if op == '':
                break
            
            try:
                select_idx = int(op)
                select = res[select_idx]
                print('Select:')
                print(res_text[select_idx])
                source = select['source']
            except Exception as e:
                print("An error occurred:", e.__class__.__name__)
                continue
            
            chunk_infos, chunk_infos_text = self.get_doc_chunks(source)
            while True:
                print(self.doc_op_help)

                op = input()

                if op == '':
                    break

                if op == '1':
                    win32api.ShellExecute(0, 'open', os.path.join(self.doc_dir, source), '', '', 1)
                    self.doc_conversation(source, chunk_infos)
                elif op == '2':
                    win32api.ShellExecute(0, 'open', os.path.join(self.doc_dir, source), '', '', 1)
                elif op == '3':
                    print('\n'.join(chunk_infos_text))
                elif op == '4':
                    self.doc_conversation(source, chunk_infos)
                elif op == '5':
                    pass

                    print(self.add_tags_help)

                    op = input()
                    act = op.split('=')
                    if len(act) > 1:
                        act_type = act[0]
                        try:
                            tags = act[1][1:-1].split(',')
                        except Exception as e:
                            print("An error occurred:", e.__class__.__name__)
                            continue

                        if act_type == 'add_tag':
                            self.add_tags(select, tags)
                            print('Added successfully.')
                        elif act_type == 'del_tag':
                            self.del_tags(select, tags)
                            print('Deleted successfully.')
                        else:
                            print('input error, try again')
    
    def doc_conversation(self, source, chunk_infos):
        print('Just start the conversation, press enter to exit.')

        # chunk_index = faiss.IndexFlatL2(self.emb_size)
        
        sys_qa_prompt = "You are a professional researcher, please answer my questions based on the context and your own thought."
        # check_str = 'Check whether the given statement requires retrieval of related webpage context for answering, respond with "Yes" if retrieval is necessary, or "No" if it is not necessary.\n\nExample:\ninput: What is the main content of this article?\noutput: Yes\n\ninput: Can you explain your answer?\noutput: No\n\n'
        # sys_qa_prompt = f"Answer the question in {self.language}. If unable to answer, please output 'No'."

        ans = ''
        while True:
            op = input('Q:')

            if op == '':
                print('Exit conversation.')
                break
            
            # question = f'A:{ans}\nQ:{op}' # Rewrite the question based on the {ans} and the {op}.
            question = op
            question = self.llm_op.prompt_generation(f'{question}\nRewrite the question.')
            print(question)
            # check_ans = self.llm_op.get_gpt_res(check_str + 'input:{}\noutput:'.format(op))
            # print(check_ans)
            # print(op)
            # if 'Yes' in check_ans:

            contexts = []
            # for i, idx in enumerate(filtered_indices):
            for idx in range(len(chunk_infos)):
                chunk = chunk_infos[idx]
                page_span = chunk['page_span']
                chunk_id = chunk['chunk_id']
                chunk_text = chunk['chunk_text']

                # Answer the question "{}" based on the relevant contexts.
                prompt = f'page_span: {page_span}\nchunk_id: {chunk_id}\nchunk_text: {chunk_text}\n'
                ans = self.llm_op.prompt_generation(prompt + f"Answer the {question} in {self.language}. If unable to answer, please output 'No'.", sys_prompt=sys_qa_prompt)
                tmp = ans[:5]
                if ('No' in tmp) or ('no' in tmp) or ('NO' in tmp):
                    # print('no related sentences')
                    # print('-'*50)
                    continue
                chunk_ans = f'page_span: {page_span}\nchunk_id: {chunk_id}\nchunk_ans: {ans}'
                print(chunk_ans)
                print(self.delimiter)
                contexts.append(chunk_ans)

            # print()
            if len(contexts) > 0:
                ans = self.mapreduce_generation(contexts)
            else:
                ans = self.llm_op.prompt_generation(f'Answer {question} in {self.language}')

            print('A:', ans)
            print(self.delimiter)
            # qa_messages.append({"role": "assistant", "content": answer})

    def doc_name_search(self, doc_name):
        pass

    def chunk_conversation(self):
        sys_qa_prompt = "You are a professional researcher, please answer my questions based on the context and your own thought."

        ans = ''

        while True:
            op = input('Q:')

            if op == '':
                print('Exit conversation.')
                break

            question = f'A:{ans}\nQ:{op}'
            question = self.llm_op.prompt_generation(f'{question}\nRewrite the question.')
            print(question)

            question_emb = np.array(self.llm_op.get_embedding(question)).astype('float32').reshape(1, -1)

            k = len(self.id2chunk)
            D, I = self.chunk_index.search(question_emb, k)
            D, I = D[0], I[0]
            filtered_indices = I[D < self.chunk_range_distance]
            filtered_distances = D[D < self.chunk_range_distance]

            contexts = []
            if filtered_indices is not None:
                for i, idx in enumerate(filtered_indices):
                    tmp = self.id2chunk[str(idx)]
                    source = tmp['source']
                    source_summary = tmp['source_summary']
                    page_span = tmp['page_span']
                    chunk_id = tmp['chunk_id']
                    source_s_tags = tmp['semantic_tags']
                    source_r_tags = tmp['regular_tags']
                    chunk_text = tmp['chunk_text']
                    prompt_text = f'source: {source}\nsource_summary: {source_summary}\npage_span: {page_span}\nchunk_id: {chunk_id}\nsemantic_tags: {source_s_tags}\nregular_tags: {source_r_tags}\nchunk_text: {chunk_text}\n'
                    ans = self.llm_op.prompt_generation(prompt_text + f'Based on the context, Answer the {question} in {self.language}:', sys_prompt=sys_qa_prompt)
                    print(prompt_text)
                    print('chunk_ans:', ans)
                    print(f'distance: {filtered_distances[i]}\n{self.delimiter}')
                    contexts.append(ans)

            if len(contexts) > 0:
                ans = self.mapreduce_generation(contexts)
            else:
                ans = self.llm_op.prompt_generation(f'Answer {question} in {self.language}')

            print('A:', ans)
            print(self.delimiter)

    def semantic_search(self, op):

        # index = self.doc_index
        # id2search = self.id2doc
        # name2id = self.doc2id
        # distance_threshold = self.doc_range_distance

        query = self.query_pattern.findall(op)
        s_tags = self.semantic_tag_pattern.findall(op)
        no_s_tags = self.no_semantic_tag_pattern.findall(op)
        r_tags = self.regular_tag_pattern.findall(op)
        no_r_tags = self.no_regular_tag_pattern.findall(op)

        filtered_indices = None
        if len(query) > 0:
            query = query[0]
            query_emb = np.array(self.llm_op.get_embedding(query)).astype('float32').reshape(1, -1)

            # lims, D, I = index.range_search(query_emb, self.doc_range_distance)
            # print(len(id2search))
            k = len(self.id2doc)
            D, I = self.doc_index.search(query_emb, k)
            
            D, I = D[0], I[0]

            filtered_indices = I[D < self.doc_range_distance]
            filtered_distances = D[D < self.doc_range_distance]

        tag_res_ids = None
        # print(tag_res_ids)
        res = []
        res_text = []
        if filtered_indices is not None:
            cnt = 0
            for i, idx in enumerate(filtered_indices):
                if (tag_res_ids is not None) and (idx not in tag_res_ids):
                    continue
                tmp = self.id2doc[str(idx)]
                source = tmp['source']
                summary = tmp['summary']
                page_nums = tmp['page_nums']
                chunk_nums = tmp['chunk_nums']
                source_s_tags = tmp['semantic_tags']
                source_r_tags = tmp['regular_tags']
                res.append(tmp)
                res_text.append(f'id: {cnt}\nsource: {source}\nsummary: {summary}\npage_nums: {page_nums}\nchunk_nums: {chunk_nums}\nsemantic_tags: {source_s_tags}\nregular_tags: {source_r_tags}\ndistance: {filtered_distances[i]}\n{self.delimiter}')
                cnt += 1
        elif tag_res_ids is not None:
            # print(tag_res_ids)
            for i, idx in enumerate(tag_res_ids):
                tmp = self.id2doc[str(idx)]
                res.append(tmp)
                print(i)
                print(tmp)
                print('-'*50)

        return res, res_text
        
    def create_semantic_tag(self):
        pass

    def add_tags(self, select, tags):

        doc_node_set = set()
        page_node_set = set()

        if select is not None:
            doc_node = self.db.get_nodes('doc', select['name']).first()
            page_nodes = self.db.get_nodes('page', select['name'])
        
            doc_node_set.add(doc_node)
            for page_node in page_nodes:
                page_node_set.add(page_node)

        for tag in tags:
            tag = tag.strip().split('|')
            tag_name = tag[0]
            print('add', tag_name)
            tag_node = self.db.create_node('tag', tag_name)

            if select is not None:
                self.db.create_relation(doc_node, tag_node, 'has_tag')
                for page_node in page_nodes:
                    self.db.create_relation(page_node, tag_node, 'has_tag')

            if (select is None) or ((len(tag) > 1) and (tag[1] == 'similar')):
                res = self.semantic_search("query=[{}]".format(tag_name))

                for res_tmp in res:
                    sim_doc_node = self.db.get_nodes('doc', res_tmp['name']).first()
                    sim_page_nodes = self.db.get_nodes('page', res_tmp['name'])

                    doc_node_set.add(sim_doc_node)
                    self.db.create_relation(sim_doc_node, tag_node, 'has_tag')

                    for sim_page_node in sim_page_nodes:
                        page_node_set.add(sim_page_node)
                        self.db.create_relation(sim_page_node, tag_node, 'has_tag')

        # doc
        for tmp_node in list(doc_node_set):
            tag_rels = self.db.relationship_matcher.match((tmp_node, None), "has_tag")

            tag_name_list = [rel.end_node["name"] for rel in tag_rels]
            tags_str = ','.join(tag_name_list)
            tmp_node['tags'] = tags_str
            self.db.graph.push(tmp_node)

            node_id = self.doc2id[tmp_node['name']]
            self.id2doc[str(node_id)]['tags'] = tags_str

        with open('cache/id2doc.json', 'w', encoding='utf-8') as f:
            json.dump(self.id2doc, f)

        # page
        for tmp_node in list(page_node_set):
            tag_rels = self.db.relationship_matcher.match((tmp_node, None), "has_tag")

            tag_name_list = [rel.end_node["name"] for rel in tag_rels]
            tags_str = ','.join(tag_name_list)
            tmp_node['tags'] = tags_str
            self.db.graph.push(tmp_node)

            node_id = self.page2id[tmp_node['name'] + ' ' + str(tmp_node['page_id'])]
            self.id2page[str(node_id)]['tags'] = tags_str

        with open('cache/id2page.json', 'w', encoding='utf-8') as f:
            json.dump(self.id2page, f)

        self.tag_list = self.get_node_name('tag')
    
    def del_tags(self, select, tags):
        if select is None:
            for tag in tags:
                tag_name = tag.strip()
                print('del', tag_name)
                # tag_node = self.db.get_nodes('tag', tag_name).first()
                self.db.delete_node('tag', tag_name)
            return

        doc_node = self.db.get_nodes('doc', select['name']).first()
        page_nodes = self.db.get_nodes('page', select['name'])

        for tag in tags:
            tag_name = tag.strip()
            print('del', tag_name)

            tag_node = self.db.get_nodes('tag', tag_name).first()

            self.db.delete_relation(doc_node, tag_node, 'has_tag')
            for page_node in page_nodes:
                self.db.delete_relation(page_node, tag_node, 'has_tag')

        tag_rels = self.db.relationship_matcher.match((doc_node, None), "has_tag")

        tag_name_list = [rel.end_node["name"] for rel in tag_rels]
        tags_str = ','.join(tag_name_list)
        doc_node['tags'] = tags_str
        self.db.graph.push(doc_node)

        node_id = self.doc2id[doc_node['name']]
        self.id2doc[str(node_id)]['tags'] = tags_str
        with open('cache/id2doc.json', 'w', encoding='utf-8') as f:
            json.dump(self.id2doc, f)

        for page_node in page_nodes:
            tag_rels = self.db.relationship_matcher.match((page_node, None), "has_tag")

            tag_name_list = [rel.end_node["name"] for rel in tag_rels]
            tags_str = ','.join(tag_name_list)
            page_node['tags'] = tags_str
            self.db.graph.push(page_node)

            node_id = self.page2id[page_node['name'] + ' ' + str(page_node['page_id'])]
            self.id2page[str(node_id)]['tags'] = tags_str
        
        with open('cache/id2page.json', 'w', encoding='utf-8') as f:
            json.dump(self.id2page, f)

    def chose_document(self):
        pass

    def get_page_doc(self, name):
        doc_node = self.db.get_nodes('doc', name).first()

        print('doc:', doc_node['name'])
        print('summary:', doc_node['summary'])
        print('tags:', doc_node['tags'])
        print('================================')

    def get_doc_chunks(self, source):
        self.db.open()
        chunks = self.db.search('chunks_table', conditions={"source": source})
        self.db.close()

        chunk_infos = []
        chunk_infos_text = []
        for chunk in chunks:
            # page_embs.append(page_node['embedding'])
            chunk_infos.append({'page_span': chunk[1], 'chunk_id': chunk[2], 'chunk_text': chunk[3], 'chunk_summary': chunk[4]})
            chunk_infos_text.append(f'page_span: {chunk[1]}\nchunk_id: {chunk[2]}\nchunk_text: {chunk[3]}\n\nchunk_summary: {chunk[4]}\n{self.delimiter}')
        
        # sorted_chunk_infos = sorted(chunk_infos, key=lambda x: x['page_id'])
        # return np.array(page_embs).astype('float32'), page_infos
        return chunk_infos, chunk_infos_text
    
    def get_chunks(self, source, pages_list, chunk_size=1024, chunk_overlap=256):

        chunks = []

        page_lens = []
        pages_tokens = []
        for idx, page in enumerate(pages_list):
            page_tokens = self.tokenizer.encode(page)
            # page_token_count = len(page_tokens)
            # page_split = page.split(' ')
            pages_tokens.extend(page_tokens)
            page_lens.append(len(pages_tokens))

        start = 0
        add = chunk_size - chunk_overlap
        page_idx = 0
        page_idx_len = page_lens[page_idx]
        chunk_id = 1
        while start < len(pages_tokens):
            # print(page_idx)
            # print(start, len(pages_tokens))
            while start >= page_idx_len:
                page_idx += 1
                page_idx_len = page_lens[page_idx]

            page_span = [str(page_idx + 1)]
            span = 0
            # print(page_lens[page_idx + span])
            while (start + chunk_size > page_lens[page_idx + span]) and (start + chunk_size < len(pages_tokens)):
                span += 1
                page_span.append(str(page_idx + 1 + span))
            page_span = ','.join(page_span)
            # if (start + chunk_size <= page_idx_len) or (start + chunk_size >= len(pages_tokens)):
            #         page_ids = str(page_idx + 1)
            # else:
            #     page_ids = str(page_idx + 1) + ',' + str(page_idx + 2)

            chunk = {'source': source, 'page_span': page_span, 'chunk_id': chunk_id, 'chunk_text': self.tokenizer.decode(pages_tokens[start:start+chunk_size])}
            chunks.append(chunk)
            chunk_id += 1
            # print(chunk)
            # print(self.delimiter)

            if (start + chunk_size >= len(pages_tokens)):
                break

            start = start + add

            # print((start + chunk_size >= len(pages_tokens)))
        # print(asd)

        return chunks
    
    def mapreduce_generation(self, new_spans, prompt="{}\nMerge the paragraphs above.{}", span=8, span_overlap=2):
        
        print('span nums:',len(new_spans))

        if len(new_spans) == 0:
            return ''

        while len(new_spans) > 1:
            old_spans = new_spans
            start = 0
            add_span = span - span_overlap
            new_spans = []
            while start < len(old_spans):
                new_span = self.llm_op.prompt_generation(prompt.format(' '.join(old_spans[start:start+span]), self.language))
                new_spans.append(new_span)
                start += add_span

                print(new_span)

            print('span nums:',len(new_spans))
            print(self.delimiter)

        return new_spans[0]
    
    def add_doc(self, source, pages_list):

        # print(source)
        summary_prompt = "{}\nSummarize this paragraph in {}:"

        chunks = self.get_chunks(source, pages_list)

        # print(asd)
        page_nums = len(pages_list)
        chunk_nums = len(chunks)
        print('Page Nums:', page_nums)
        print('Chunk Nums:', chunk_nums)

        chunk_embs = []
        chunk_summaries = []
        print('Process Chunks...')
        for i, chunk in enumerate(chunks):
            chunk_text = chunk['chunk_text']
            text = f"source: {chunk['source']}\npage_span: {chunk['page_span']}\nchunk_id: {chunk['chunk_id']}\nchunk_text: {chunk_text}"
            chunk_emb = self.llm_op.get_embedding(text)
            chunk_embs.append(chunk_emb)
            
            chunk_summary = self.llm_op.prompt_generation(summary_prompt.format(text, self.language))
            chunk_summaries.append(chunk_summary)

            chunks[i]['summary'] = chunk_summary
            chunks[i]['embedding'] = pickle.dumps(chunk_emb)

            print(text)
            print()
            # print('chunk {}:'.format(i+1), 'page {}:'.format(chunk['page_span']), chunk_summary)
            print('chunk_summary:', chunk_summary)
            print(self.delimiter)
        print('Done.')

        # print('Process Chunks...')
        # for i in range(len(chunks)):
        #     chunk_text = chunks[i]['chunk_text']
        #     chunk_emb = self.llm_op.get_embedding(chunk_text)
        #     chunks[i]['chunk_emb'] = pickle.dumps(chunk_emb)
        # print('Done.')

        doc_emb = list(np.mean(np.array(chunk_embs), axis=0))
        doc_summary = self.mapreduce_generation(chunk_summaries)

        print('Doc Summary:', doc_summary)

        # print(asd)
        
        print('Process Similarily Tags...')
        add_tags_list = []
        if self.tag_index is not None:
            D, I = self.tag_index.search(doc_emb, len(self.semantic_tags_list))
            D, I = D[0], I[0]

            filtered_indices = I[D < self.doc_range_distance]
            filtered_distances = D[D < self.doc_range_distance]

            if filtered_indices is not None:
                for i, idx in enumerate(filtered_indices):
                    tag = self.semantic_tags_list[idx]
                    print('similar tag:', tag)
                    print('distance:', filtered_distances[i])
                    print('-'*50)
                    add_tags_list.append(tag)
        print('Add Similarily Tag Nums:', len(add_tags_list))
        
        print('Inserting to DB...')
        self.db.open()
        self.db.insert('docs_table', {"source": source, "summary": doc_summary, "page_nums": page_nums, "chunk_nums": chunk_nums, "embedding": pickle.dumps(doc_emb)})
        # for i, chunk in enumerate(chunks):
        #     self.db.insert('chunks_table', {"source": source, "page_span": str(i+1), "page_text": pages_list[i], "summary": page_summaries[i], "embedding": pickle.dumps(page_embs[i])})
        for chunk in chunks:
            self.db.insert('chunks_table', chunk)
        for tag in add_tags_list:
            self.db.insert('semantic_tags2source_table', {"tag": tag, "source": source})
        self.db.close()
        print('Done.')

        # print(asd)

    def del_doc(self, source):
        self.db.open()
        self.db.delete('docs_table', {"source": source})
        self.db.delete('pages_table', {"source": source})
        self.db.delete('chunks_table', {"source": source})
        self.db.close()