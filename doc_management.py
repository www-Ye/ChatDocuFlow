from db_operater import Neo4j_DB, Sqlite_DB
from openai_operater import Openai_Operater
import numpy as np
import win32api
import faiss
import json
import os
import fitz
import re

class Doc_Management:
    def __init__(self, args):
        self.doc_dir = args.doc_dir
        self.language = args.language
        
        if args.db_type == 'neo4j':
            self.db = Neo4j_DB(args.user, args.password)
        elif args.db_type == 'sqlite':
            self.db = Sqlite_DB(args.db_name)

        self.openai_op = Openai_Operater(args.openai_key, args.proxy)

        self.query_pattern = re.compile(r'query=\[(.*?)\]')
        self.tag_pattern = re.compile(r'has_tag=\[(.*?)\]')
        self.no_tag_pattern = re.compile(r'no_tag=\[(.*?)\]')

        self.emb_size = 1536
        self.doc_range_distance = args.doc_range_distance
        self.page_range_distance = args.page_range_distance

        self.doc_list = self.get_node_name('doc')
        self.tag_list = self.get_node_name('tag')
        # print(self.tag_list)

        self.update_doc()

        # if (args.language == 'English') or args.language == 'english':
        self.action_help = '''Choose your action:

1. Document search - Retrieve relevant documents based on query and tags.
2. Page-level conversation - Retrieve answers to questions based on relevant pages. (To be added.)
3. Add/update semantic tags - Automatically associate similar documents with tags.
4. Update documents - Update PDF files in the system's folder (automatically done each time the system is started).
Press Enter to exit the system.'''

        self.doc_search_help = '''The query should be entered in the following format:

query=[] has_tag=[] no_tag=[]

All parts items cannot be omitted at the same time. Multiple tags can be separated by ',' in [].

* "query=[]" specifies a search query that you want to perform.
* "has_tag=[]" specifies a list of tags that the documents should have.
* "no_tag=[]" specifies a list of tags that the documents should not have.

Press Enter to go back to the previous level.'''

        self.add_tags_help = '''Manually add semantic tags, multiple tags can be separated by commas, and the specific format is as follows:
* "add_tag=[xxx,yyy|similar,zzz]" means adding tags, where |similar indicates adding documents that are semantically similar to the tag.
* "del_tag=[xxx,yyy]" means deleting tags.

Press Enter to return.'''

#         elif (args.language == 'Chinese') or args.language == 'chinese':
#             self.action_help = '''选择你的操作：

# 1. 文档搜索 - 根据query、tag选择检索相关文档
# 2. 页面级问答 - 根据问题检索相关页面回答问题
# 3. 添加/更新语义标签 - 自动将相似文档与标签进行关联
# 4. 更新文档 - 将文件夹中的pdf更新至系统（每次启动系统会自动更新）
# 输入回车键退出系统。'''
    
    def update_doc(self):
        file_list = os.listdir(self.doc_dir)

        tmp_diff = set(file_list) - set(self.doc_list)
        add_list = list(tmp_diff)

        tmp_diff = set(self.doc_list) - set(file_list)
        del_list = list(tmp_diff)

        # print(self.doc_list)
        # file_nums = len(file_list)
        # print('file nums:', file_nums)
        # print('add nums:', len(add_list))
        # print('del nums:', len(del_list))
        self.doc_nums = len(self.doc_list)

        add_nums = 0
        for item in add_list:
            if(item.endswith('.pdf')):
                print('Add {} to the DB'.format(item))
                text_list = self.parse_pdf(os.path.join(self.doc_dir, item))

                self.add_doc(item, text_list)

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

        if (len(add_list) > 0) or (len(del_list) > 0):
            self.update_embs()
        else:
            with open('cache/id2doc.json', 'r', encoding='utf-8') as f:
                self.id2doc = json.load(f)
            with open('cache/doc2id.json', 'r', encoding='utf-8') as f:
                self.doc2id = json.load(f)
            self.doc_index = faiss.read_index("cache/doc_index.faiss")

            with open('cache/id2page.json', 'r', encoding='utf-8') as f:
                self.id2page = json.load(f)
            with open('cache/page2id.json', 'r', encoding='utf-8') as f:
                self.page2id = json.load(f)
            self.page_index = faiss.read_index("cache/page_index.faiss")

        # return file_nums
    
    def update_embs(self):

        # embedding doc
        doc_nodes = self.db.get_nodes('doc')
        self.id2doc = {}
        self.doc2id = {}
        doc_embs = []
        for i, doc_node in enumerate(doc_nodes):
            name = doc_node['name']
            summary = doc_node['summary']
            tags = doc_node['tags']
            self.id2doc[str(i)] = {'name': name, 'summary': summary, 'tags': tags}
            self.doc2id[name] = i
            doc_embs.append(doc_node['embedding'])
        with open('cache/id2doc.json', 'w', encoding='utf-8') as f:
            json.dump(self.id2doc, f)
        with open('cache/doc2id.json', 'w', encoding='utf-8') as f:
            json.dump(self.doc2id, f)
        if len(doc_embs) > 0:
            doc_embs = np.array(doc_embs).astype('float32')
            self.doc_index = faiss.IndexFlatL2(self.emb_size)
            self.doc_index.add(doc_embs)
            faiss.write_index(self.doc_index, "cache/doc_index.faiss")

        # embedding page
        page_nodes = self.db.get_nodes('page')
        self.id2page = {}
        self.page2id = {}
        page_embs = []
        for i, page_node in enumerate(page_nodes):
            name = page_node['name']
            page_id = page_node['page_id']
            # summary = page_node['summary']
            tags = page_node['tags']
            self.id2page[str(i)] = {'name': name, 'page_id': page_id, 'tags': tags}
            self.page2id[name + ' ' + str(page_id)] = i
            page_embs.append(page_node['embedding'])
        with open('cache/id2page.json', 'w', encoding='utf-8') as f:
            json.dump(self.id2page, f)
        with open('cache/page2id.json', 'w', encoding='utf-8') as f:
            json.dump(self.page2id, f)
        if len(page_embs) > 0:
            page_embs = np.array(page_embs).astype('float32')
            self.page_index = faiss.IndexFlatL2(self.emb_size)
            self.page_index.add(page_embs)
            faiss.write_index(self.page_index, "cache/page_index.faiss")

    def parse_pdf(self, path):
        item_pdf = fitz.open(path) # pdf document
        text_list = [page.get_text().replace('\n', ' ') for page in item_pdf]

        return text_list
    
    def search_doc(self, op, search_type='doc'):
        res = self.semantic_search(op, search_type)

        while (len(res) > 0):

            print('Open the document corresponding to the input ID. Press enter to go back.')
            op = input()

            if op == '':
                break
            
            try:
                select = res[int(op)]
                print('Select:')
                print(select)
                print('-' * 50)
                name = select['name']
            except Exception as e:
                print("An error occurred:", e.__class__.__name__)
                continue

            while True:
                print('''Choose your action:

1. Open the document and enter conversation mode
2. Only open the document
3. Only enter conversation mode
4. Add/Del tags
Press enter to go back.''')

                op = input()

                if op == '':
                    break

                if op == '1':
                    win32api.ShellExecute(0, 'open', os.path.join(self.doc_dir, name), '', '', 1)
                    page_embs, page_infos = self.get_doc_pages(name)
                    self.doc_conversation(page_embs, page_infos)
                elif op == '2':
                    win32api.ShellExecute(0, 'open', os.path.join(self.doc_dir, name), '', '', 1)
                elif op == '3':
                    page_embs, page_infos = self.get_doc_pages(name)
                    self.doc_conversation(page_embs, page_infos)
                elif op == '4':
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
    
    def doc_conversation(self, page_embs, page_infos):
        print('Just start the conversation, press enter to exit.')

        page_index = faiss.IndexFlatL2(self.emb_size)
        # print(page_embs.shape)
        # print(page_embs)
        page_index.add(page_embs)
        k = page_embs.shape[0]
        
        qa_messages = [{"role": "system", "content": "You are a professional researcher, please answer my questions based on the context."}]
        check_str = 'Check whether the given statement requires retrieval of related webpage context for answering, respond with "Yes" if retrieval is necessary, or "No" if it is not necessary.\n\nExample:\ninput: What is the main content of this article?\noutput: Yes\n\ninput: Can you explain your answer?\noutput: No\n\n'
        threshold = 0.6

        # page_infos = sorted(page_infos, key=lambda item: item['page_id'])
        # print(sorted_by_value)


        while True:
            op = input('Q:')

            if op == '':
                print('Exit conversation.')
                break
            

            check_ans = self.openai_op.get_gpt_res(check_str + 'input:{}\noutput:'.format(op))
            # print(check_ans)
            # print(op)
            if 'Yes' in check_ans:
                query_emb = np.array(self.openai_op.get_embedding(op)).astype('float32').reshape(1, -1)
                # print(query_emb)
                D, I = page_index.search(query_emb, k)
                D, I = D[0], I[0]
                filtered_indices = I[D < threshold]
                filtered_distances = D[D < threshold]

                # print(filtered_indices, filtered_distances)
                contexts = []
                for i, idx in enumerate(filtered_indices):
                # for i, idx in enumerate(range(len(page_infos))):
                    sim_page = page_infos[idx]
                    print('page_id:', sim_page['page_id'], ' distance:', filtered_distances[i])
                    # print('-'*50)
                    # Answer the question "{}" based on the relevant contexts.
                    prompt = 'Text:{}\n{}'.format(sim_page['text'], op)
                    sents = self.openai_op.get_gpt_res(prompt)
                    if ('Sorry' in sents) or ('sorry' in sents):
                        print('no related sentences')
                        continue
                    print(sents)
                    contexts.append('page {}: '.format(sim_page['page_id']) + sents)

                print()
                context = 'Relevant sentences:' + '\n'.join(contexts) + '\n'
                prompt = context + 'Answer the question "{}" in {} based on the relevant contexts in the paper.'.format(op, self.language)
            else:
                prompt = op
            # print('prompt:', prompt)
            qa_messages.append({"role": "user", "content": prompt})

            answer = self.openai_op.conversation(qa_messages)

            print('A:', answer)
            print('-' * 50)
            qa_messages.append({"role": "assistant", "content": answer})

    def doc_name_search(self, doc_name):
        pass

    def semantic_search(self, op, search_type='doc'):

        if search_type == 'doc':
            index = self.doc_index
            id2search = self.id2doc
            name2id = self.doc2id
            distance_threshold = self.doc_range_distance
        elif search_type == 'page':
            index = self.page_index
            id2search = self.id2page
            name2id = self.page2id
            distance_threshold = self.page_range_distance

        query = self.query_pattern.findall(op)
        filtered_indices = None
        if len(query) > 0:
            query = query[0]
            query_emb = np.array(self.openai_op.get_embedding(query)).astype('float32').reshape(1, -1)

            # lims, D, I = index.range_search(query_emb, self.doc_range_distance)
            # print(len(id2search))
            k = len(id2search)
            D, I = index.search(query_emb, k)
            
            D, I = D[0], I[0]
            # print(D, I)

            filtered_indices = I[D < distance_threshold]
            filtered_distances = D[D < distance_threshold]
    
        tags = self.tag_pattern.findall(op)
        no_tags = self.no_tag_pattern.findall(op)
        
        condition = []
        if (len(tags) > 0):
            tags = tags[0].split(',')
            tags = ["'" + tag + "'" for tag in tags]
            condition.append('t.name IN [{}]'.format(','.join(tags)))
        if len(no_tags) > 0:
            no_tags = no_tags[0].split(',')
            no_tags_str = []
            for no_tag in no_tags:
                tmp_str = "NOT (n)-[:has_tag]->(:tag {name:'" + no_tag + "'})"
                # NOT (d)-[:has_tag]->(:tag {name: 'chatgpt'})
                # print(tmp_str)
                no_tags_str.append(tmp_str)
            condition.append(' AND '.join(no_tags_str))

        tag_res_ids = None
        if len(condition) > 0:
            if search_type == 'doc':
                cypher_str = 'MATCH (n:doc)-[:has_tag]->(t:tag) WHERE {} RETURN n.name'.format(' AND '.join(condition))
                # print(cypher_str)
                node_res = self.db.execute_cypher(cypher_str)
                # print(node_res)
                tag_res_ids = set()
                for n in node_res:
                    tag_res_ids.add(name2id[n['n.name']])
                tag_res_ids = list(tag_res_ids)

            elif search_type == 'page':
                cypher_str = 'MATCH (n:page)-[:has_tag]->(t:tag) WHERE {} RETURN n.name, n.page_id'.format(' AND '.join(condition))
                node_res = self.db.execute_cypher(cypher_str)
                # print(node_res)
                # for n in node_res:
                #     print(n)
                # tag_res_ids = [name2id[n['name'] + ' ' + str(n['page_id'])] for n in node_res]
                tag_res_ids = set()
                for n in node_res:
                    tag_res_ids.add(name2id[n['name'] + ' ' + str(n['page_id'])])
                tag_res_ids = list(tag_res_ids)

        # print(tag_res_ids)
        res = []
        if filtered_indices is not None:
            cnt = 0
            for i, idx in enumerate(filtered_indices):
                if (tag_res_ids is not None) and (idx not in tag_res_ids):
                    continue
                tmp = id2search[str(idx)]
                res.append(tmp)
                print(cnt)
                print(tmp)
                print('distance:', filtered_distances[i])
                print('-'*50)
                cnt += 1
        elif tag_res_ids is not None:
            # print(tag_res_ids)
            for i, idx in enumerate(tag_res_ids):
                tmp = id2search[str(idx)]
                res.append(tmp)
                print(i)
                print(tmp)
                print('-'*50)

        print('Number of search results:', len(res))
        return res
        

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
                res = self.semantic_search("query=[{}]".format(tag_name), 'doc')

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

    def get_doc_pages(self, name):
        page_nodes = self.db.get_nodes('page', name)

        page_embs = []
        page_infos = []
        for page_node in page_nodes:
            page_embs.append(page_node['embedding'])
            page_infos.append({'page_id': page_node['page_id'], 'text': page_node['text']})
        
        return np.array(page_embs).astype('float32'), page_infos
    
    def get_node_name(self, node_type='doc'):
        nodes = self.db.get_nodes(node_type)
        names = [n['name'] for n in nodes]
        return names
    
    def add_doc(self, item, text_list):
        # page_node
        embs = []
        summaries = []
        print('page nums:', len(text_list))
        for i, text in enumerate(text_list):
            emb = self.openai_op.get_embedding(text)
            embs.append(emb)
            
            if i == 0:
                summary = self.openai_op.summary_para(text, self.language)
                summaries.append(summary)
                # print('page {}:'.format(i+1), summary)
                print('summary:', summary)
                print('================================')
            # break
        
        doc_emb = embs[0]
        doc_summary = summaries[0]
        doc_node = self.db.create_node('doc', item, doc_emb, doc_summary, tags="")

        for i in range(len(text_list)):
            page_node = self.db.create_node('page', item, embs[i], text=text_list[i], page_id=i+1, tags="")
            self.db.create_relation(doc_node, page_node, 'has_page')

    def del_doc(self, item):
        self.db.delete_node('doc', item)
        self.db.delete_node('page', item)