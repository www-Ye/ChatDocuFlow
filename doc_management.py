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
        self.tag_pattern = re.compile(r'tag=\[(.*?)\]')
        self.no_tag_pattern = re.compile(r'no_tag=\[(.*?)\]')

        self.emb_size = 1536
        self.range_distance = args.range_distance

        self.doc_list = self.get_node_name('doc')
        self.tag_list = self.get_node_name('tag')
        # print(self.tag_list)

        self.file_nums = self.update_doc()

        self.search_help = '''The query should be entered in the following format:

query=[] tag=[] no_tag=[]

All parts items cannot be omitted at the same time. Multiple tags can be separated by ',' in [].

* "query=[]" specifies a search query that you want to perform.
* "tag=[]" specifies a list of tags that the documents should have.
* "no_tag=[]" specifies a list of tags that the documents should not have.

Press Enter to go back to the previous level.'''

        self.add_tags_help = '''Manually add semantic tags, multiple tags can be separated by commas, and the specific format is as follows:
* "add_tag=[xxx,yyy|similar,zzz]" means adding tags, where |similar indicates adding documents/pages that are semantically similar to the tag.
* "del_tag=[xxx,yyy]" means deleting tags.

Press Enter to return.'''
    
    def update_doc(self):
        file_list = os.listdir(self.doc_dir)

        tmp_diff = set(file_list) - set(self.doc_list)
        add_list = list(tmp_diff)

        tmp_diff = set(self.doc_list) - set(file_list)
        del_list = list(tmp_diff)

        # print(self.doc_list)
        file_nums = len(file_list)
        print('file nums:', file_nums)
        print('add nums:', len(add_list))
        print('del nums:', len(del_list))

        for item in add_list:
            if(item.endswith('.pdf')):
                print('Add {} to the DB'.format(item))
                text_list = self.parse_pdf(os.path.join(self.doc_dir, item))

                self.add_doc(item, text_list)

        for item in del_list:
            print('Delete {} from the DB'.format(item))
            self.del_doc(item)

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

        return file_nums
    
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
            summary = page_node['summary']
            tags = page_node['tags']
            self.id2page[str(i)] = {'name': name, 'page_id': page_id, 'summary': summary, 'tags': tags}
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
    
    def search(self, op, search_type='doc'):
        res = self.semantic_search(op, search_type)
        # try:
        #     res = self.semantic_search(op, search_type)
        # except Exception as e:
        #     print("An error occurred:", e.__class__.__name__)

        print('Open the document corresponding to the input ID.')
        op = input()
        flag = False

        try:
            select = res[int(op)]
            print('open')
            print(select)
            name = select['name']
            win32api.ShellExecute(0, 'open', os.path.join(self.doc_dir, name), '', '', 1)
            flag = True
        except Exception as e:
            print("An error occurred:", e.__class__.__name__)

        if flag:
            if search_type == 'doc':
                print('If you want to display a summary of each page of the document, enter 1. Otherwise, press Enter.')
                op = input()
                if op == '1':
                    self.get_doc_pages(name)
            elif search_type == 'page':
                self.get_page_doc(name)
                # print('If you want to display a summary of the document, enter 1. Otherwise, press Enter.')
                # op = input()
                # if op == '1':
                #     self.get_page_doc(name)

            while True:
                print(self.add_tags_help)
            
                op = input()

                act = op.split('=')

                if len(act) > 1:
                    act_type = act[0]
                    tags = act[1][1:-1].split(',')

                    if act_type == 'add_tag':
                        self.add_tags(select, tags, search_type)
                        print('Added successfully.')
                        break
                    elif act_type == 'del_tag':
                        self.del_tags(select, tags, search_type)
                        print('Deleted successfully.')
                        break
                    else:
                        print('input error, try again')
                else:
                    break

    def doc_name_search(self, doc_name):
        pass

    def semantic_search(self, op, search_type='doc'):

        if search_type == 'doc':
            index = self.doc_index
            id2search = self.id2doc
            name2id = self.doc2id
        elif search_type == 'page':
            index = self.page_index
            id2search = self.id2page
            name2id = self.page2id

        query = self.query_pattern.findall(op)
        I = None
        if len(query) > 0:
            query = query[0]
            query_emb = np.array(self.openai_op.get_embedding(query)).astype('float32').reshape(1, -1)

            lims, D, I = index.range_search(query_emb, self.range_distance)
            # D, I = index.search(query_emb, 10)
            # D, I = D[0], I[0]
    
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
                tmp_str = "NOT (n)-[:has_tag]->(:tag{name:'" + no_tag + "'})"
                # print(tmp_str)
                no_tags_str.append(tmp_str)
            condition.append(' AND '.join(no_tags_str))

        tag_res_ids = None
        if len(condition) > 0:
            if search_type == 'doc':
                cypher_str = 'MATCH (n:doc)-[:has_tag]->(t:tag) WHERE {} RETURN n.name'.format(' AND '.join(condition))
                node_res = self.db.execute_cypher(cypher_str)
                tag_res_ids = [name2id[n['n.name']] for n in node_res]

            elif search_type == 'page':
                cypher_str = 'MATCH (n:page)-[:has_tag]->(t:tag) WHERE {} RETURN n.name, n.page_id'.format(' AND '.join(condition))
                node_res = self.db.execute_cypher(cypher_str)
                # print(node_res)
                # for n in node_res:
                #     print(n)
                tag_res_ids = [name2id[n['n.name'] + ' ' + str(n['n.page_id'])] for n in node_res]

        res = []
        if I is not None:
            cnt = 0
            for i, idx in enumerate(I):
                if (tag_res_ids is not None) and (idx not in tag_res_ids):
                    continue
                tmp = id2search[str(idx)]
                res.append(tmp)
                print(cnt)
                print(tmp)
                print('distance:', D[i])
                print('-'*50)
                cnt += 1
        else:
            # print(tag_res_ids)
            for i, idx in enumerate(tag_res_ids):
                tmp = id2search[str(idx)]
                res.append(tmp)
                print(i)
                print(tmp)
                print('-'*50)

        return res
        

    def create_semantic_tag(self):
        pass

    def add_tags(self, select, tags, node_type='doc'):

        node_set = set()

        if select is not None:
            if node_type == 'doc':
                node = self.db.get_nodes(node_type, select['name']).first()
            elif node_type == 'page':
                node = self.db.get_nodes(node_type, select['name'], select['page_id']).first()

        
            node_set.add(node)

        for tag in tags:
            tag = tag.strip().split('|')
            tag_name = tag[0]
            print('add', tag_name)
            tag_node = self.db.create_node('tag', tag_name)

            if select is not None:
                self.db.create_relation(node, tag_node, 'has_tag')

            if (select is None) or ((len(tag) > 1) and (tag[1] == 'similar')):
                res = self.semantic_search("query=[{}]".format(tag_name), node_type)

                for res_tmp in res:
                    if node_type == 'doc':
                        sim_node = self.db.get_nodes(node_type, res_tmp['name']).first()
                    elif node_type == 'page':
                        sim_node = self.db.get_nodes(node_type, res_tmp['name'], res_tmp['page_id']).first()

                    node_set.add(sim_node)
                    self.db.create_relation(sim_node, tag_node, 'has_tag')

        for tmp_node in list(node_set):
            tag_rels = self.db.relationship_matcher.match((tmp_node, None), "has_tag")

            tag_name_list = [rel.end_node["name"] for rel in tag_rels]
            tags_str = ','.join(tag_name_list)
            tmp_node['tags'] = tags_str
            self.db.graph.push(tmp_node)

            if node_type == 'doc':
                node_id = self.doc2id[tmp_node['name']]
                self.id2doc[str(node_id)]['tags'] = tags_str
            elif node_type == 'page':
                node_id = self.page2id[tmp_node['name'] + ' ' + str(tmp_node['page_id'])]
                self.id2page[str(node_id)]['tags'] = tags_str

        if node_type == 'doc':
            with open('cache/id2doc.json', 'w', encoding='utf-8') as f:
                json.dump(self.id2doc, f)
        elif node_type == 'page':
            with open('cache/id2page.json', 'w', encoding='utf-8') as f:
                json.dump(self.id2page, f)
    
    def del_tags(self, select, tags, node_type='doc'):
        if node_type == 'doc':
            node = self.db.get_nodes(node_type, select['name']).first()
        elif node_type == 'page':
            node = self.db.get_nodes(node_type, select['name'], select['page_id']).first()

        for tag in tags:
            tag_name = tag.strip()
            print('del', tag_name)

            tag_node = self.db.get_nodes('tag', tag_name).first()

            self.db.delete_relation(node, tag_node, 'has_tag')

        tag_rels = self.db.relationship_matcher.match((node, None), "has_tag")

        tag_name_list = [rel.end_node["name"] for rel in tag_rels]
        tags_str = ','.join(tag_name_list)
        node['tags'] = tags_str
        self.db.graph.push(node)

        if node_type == 'doc':
            node_id = self.doc2id[node['name']]
            self.id2doc[str(node_id)]['tags'] = tags_str
            with open('cache/id2doc.json', 'w', encoding='utf-8') as f:
                json.dump(self.id2doc, f)

        elif node_type == 'page':
            node_id = self.page2id[node['name'] + ' ' + str(node['page_id'])]
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

        page_id2summary = {}
        for page_node in page_nodes:
            page_id2summary[page_node['page_id']] = page_node['summary']
        
        sorted_page = sorted(page_id2summary.items())
        for row in sorted_page:
            print('page {}:'.format(row[0]), row[1])
            print('================================')
    
    def get_node_name(self, node_type='doc'):
        nodes = self.db.get_nodes(node_type)
        names = [n['name'] for n in nodes]
        return names
    
    def add_doc(self, item, text_list):
        # page_node
        embs = []
        summaries = []
        print(len(text_list))
        for i, text in enumerate(text_list):
            emb = self.openai_op.get_embedding(text)
            summary = self.openai_op.summary_para(text, self.language)
            embs.append(emb)
            summaries.append(summary)
            print('page {}:'.format(i+1), summary)
            print('================================')
            # break
        
        doc_emb = embs[0]
        doc_summary = summaries[0]
        doc_node = self.db.create_node('doc', item, doc_emb, doc_summary, tags="")

        for i in range(len(summaries)):
            page_node = self.db.create_node('page', item, embs[i], summaries[i], page_id=i+1, tags="")
            self.db.create_relation(doc_node, page_node, 'has_page')

    def del_doc(self, item):
        self.db.delete_node('doc', item)
        self.db.delete_node('page', item)