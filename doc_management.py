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
        self.semantic_tag_pattern = re.compile(r'tag=\[(.*?)\]')
        self.no_semantic_tag_pattern = re.compile(r'no_tag=\[(.*?)\]')
        self.attribute_pattern = re.compile(r'attribute=\[(.*?)\]')
        self.no_attribute_pattern = re.compile(r'no_attribute=\[(.*?)\]')

        self.emb_size = 1536
        self.range_distance = args.range_distance

        self.doc_list = self.get_doc()

        self.file_nums = self.update_doc()

        self.search_help = '''The query should be entered in the following format:

query=[] tag=[] no_tag=[] attribute=[] no_attribute=[]

All parts items cannot be omitted at the same time. Multiple tags can be separated by ',' in [].

* "query=[]" specifies a search query that you want to perform.
* "tag=[]" specifies a list of semantic tags that the documents should have.
* "no_tag=[]" specifies a list of semantic tags that the documents should not have.
* "attribute=[]" specifies a list of document attributes and their values that the documents should have.
* "no_attribute=[]" specifies a list of document attributes and their values that the documents should not have.

Press Enter to go back to the previous level.'''

        self.add_tag_att_help = '''Manually add semantic tags and attributes, multiple tags can be separated by commas, and the specific format is as follows:
* "add_tag=[xxx,xxx]" Add semantic tags.
* "del_tag=[xxx,xxx]" Delete semantic tags.
* "add_att=[xxx,xxx]" Add attributes.
* "del_att=[xxx,xxx]" Delete attributes.
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
            self.id2doc[str(i)] = {'name': name, 'summary': summary}
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
            self.id2page[str(i)] = {'name': name, 'page_id': page_id, 'summary': summary}
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
        # print(text_list[0])
        return text_list
    
    def search(self, op, search_type='doc'):
        try:
            res = self.semantic_search(op, search_type)
        except Exception as e:
            print("An error occurred:", e.__class__.__name__)

        print('Open the document corresponding to the input ID.')
        op = input()
        
        try:
            select = res[int(op)]
            print('open')
            print(select)
            name = select['name']
            win32api.ShellExecute(0, 'open', os.path.join(self.doc_dir, name), '', '', 1)
        except Exception as e:
            print("An error occurred:", e.__class__.__name__)

        if search_type == 'doc':
            print('If you want to display a summary of each page of the document, enter 1. Otherwise, press Enter.')
            op = input()
            if op == '1':
                self.get_doc_pages(name)

        while True:
            print(self.add_tag_att_help)
        
            op = input()

            act = op.split('=')

            if len(act) > 1:
                act_type = act[0]
                tag_att = act[1].split(',')

                if act_type == 'add_tag':
                    self.add_tag_att(select, tag_att, 'semantic_tag', search_type)
                    print('Added successfully.')
                    break
                elif act_type == 'del_tag':
                    self.del_tag_att(select, tag_att, 'semantic_tag', search_type)
                    print('Deleted successfully.')
                    break
                elif act_type == 'add_att':
                    self.add_tag_att(select, tag_att, 'attribute', search_type)
                    print('Added successfully.')
                    break
                elif act_type == 'del_att':
                    self.del_tag_att(select, tag_att, 'attribute', search_type)
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
        elif search_type == 'page':
            index = self.page_index
            id2search = self.id2page

        query = self.query_pattern.findall(op)
        if len(query) > 0:
            query = query[0]
            query_emb = np.array(self.openai_op.get_embedding(query)).astype('float32').reshape(1, -1)
            # print(query_emb)
            # print(query_emb.shape)
            lims, D, I = index.range_search(query_emb, self.range_distance)
            # D, I = index.search(query_emb, 10)
            # D, I = D[0], I[0]
            # print(lims, D, I)
            # paths = []
            # page_ids = []
            res = []
            for i, idx in enumerate(I):
                tmp = id2search[str(idx)]
                res.append(tmp)
                # paths.append(tmp['name'])
                # if search_type == 'page':
                #     page_ids.append(str(tmp['page_id']))
                print(i)
                print(tmp)
                print('distance:', D[i])
                print('-'*50)

        return res
        # tags = self.semantic_tag_pattern.findall(op).split(',')
        # no_tags = self.no_semantic_tag_pattern.findall(op).split(',')
        # properties = self.property_pattern.findall(op).split(',')
        # no_properties = self.no_property_pattern.findall(op).split(',')

        # self.db.get_search_node(search_type, tags, no_tags, properties, no_properties)
        

    def create_semantic_tag(self):
        pass

    def add_tag_att(self, select, tag_att, type='semantic_tag', node_type='doc'):
        if node_type == 'doc':
            node = self.db.get_nodes(node_type, select['name']).first()
        elif node_type == 'page':
            node = self.db.get_nodes(node_type, select['name'], select['page_id']).first()
        print(node)

        for t in tag_att:
            tmp = t.strip()
            print(tmp)
    
    def del_tag_att(self, name, tag_att, type='semantic_tag', node_type='doc'):
        pass

    def chose_document(self):
        pass

    def get_doc_pages(self, name):
        page_nodes = self.db.get_nodes('page', name)

        page_id2summary = {}
        for page_node in page_nodes:
            page_id2summary[page_node['page_id']] = page_node['summary']
        
        sorted_page = sorted(page_id2summary.items())
        for row in sorted_page:
            print('page {}:'.format(row[0]), row[1])
            print('================================')
    
    def get_doc(self):
        doc_nodes = self.db.get_nodes('doc')
        names = [doc['name'] for doc in doc_nodes]
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
        doc_node = self.db.create_node('doc', item, doc_emb, doc_summary)

        for i in range(len(summaries)):
            page_node = self.db.create_node('page', item, embs[i], summaries[i], page_id=i+1)
            self.db.create_relation(doc_node, page_node, 'has_page')

    def del_doc(self, item):
        self.db.delete_node('doc', item)
        self.db.delete_node('page', item)