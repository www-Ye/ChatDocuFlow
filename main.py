from doc_management import Doc_Management
import argparse
import time
import win32api
import os

search_help = '''The query should be entered in the following format:

query=[] tag=[] no_tag=[] attribute=[] no_attribute=[]

All parts items cannot be omitted at the same time. Multiple tags can be separated by ',' in [].

* "query=[]" specifies a search query that you want to perform.
* "tag=[]" specifies a list of semantic tags that the documents should have.
* "no_tag=[]" specifies a list of semantic tags that the documents should not have.
* "attribute=[]" specifies a list of document attributes and their values that the documents should have.
* "no_attribute=[]" specifies a list of document attributes and their values that the documents should not have.

Press Enter to go back to the previous level.'''

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--doc_dir", default="documents", type=str)
    parser.add_argument("--db_type", default="neo4j", type=str)
    parser.add_argument("--user", default="neo4j", type=str)
    parser.add_argument("--password", default="neo4j", type=str)
    parser.add_argument("--db_name", default="", type=str)
    parser.add_argument("--language", default="Chinese", type=str)
    parser.add_argument("--range_distance", default=0.6, type=float, help="The retrieval threshold returns higher similarity for closer distances.")

    parser.add_argument("--openai_key", default="", type=str)
    parser.add_argument("--proxy", default="", type=str)

    args = parser.parse_args()
    
    print('*Welcome to Document Management*')

    DM = Doc_Management(args)

    while True:
        if DM.file_nums == 0:
            print('The paper is missing in the folder. Please add the paper.')
            time.sleep(3)
            break

        print('''Please select your operation:

1. Document-level search
2. Page-level search
3. Update document data
4. Add semantic tags
Press Enter key to exit.''')

        op = input()
        if op == "":
            print('***Thank you for using.***')
            time.sleep(3)
            break

        if op == '1':
            while True:
                print(search_help)
                op = input()

                if op == "":
                    break

                try:
                    res = DM.semantic_search(op, 'doc')
                except Exception as e:
                    print("An error occurred:", e.__class__.__name__)

                print('Open the document corresponding to the input ID.')
                op = input()
                
                try:
                    select = res[int(op)]
                    print('open')
                    print(select)
                    name = select['name']
                    win32api.ShellExecute(0, 'open', os.path.join(args.doc_dir, name), '', '', 1)
                except Exception as e:
                    print("An error occurred:", e.__class__.__name__)

                print('If you want to display a summary of each page of the document, enter 1. Otherwise, press Enter.')
                op = input()
                if op == '1':
                    DM.get_doc_pages(name)

                while True:
                    print('''Manually add semantic tags and attributes, multiple tags can be separated by commas, and the specific format is as follows:
* Add semantic tags: add_tag xxx,xxx
* Delete semantic tags: del_tag xxx,xxx
* Add attributes: add_att xxx,xxx
* Delete attributes: del_att xxx,xxx
Press Enter to return.''')
                
                    op = input()

                    act = op.split(' ')

                    if len(act) > 1:
                        act_type = act[0]
                        tag_att = act[1].replace(' ', '').split(',')

                        if act_type == 'add_tag':
                            DM.add_semantic_tag(name, tag_att)
                            print('Added successfully.')
                            break
                        elif act_type == 'del_tag':
                            DM.del_semantic_tag(name, tag_att)
                            print('Added successfully.')
                            break
                        elif act_type == 'add_att':
                            DM.add_attribute(name, tag_att)
                            print('Added successfully.')
                            break
                        elif act_type == 'del_att':
                            DM.del_attribute(name, tag_att)
                            print('Added successfully.')
                            break
                        else:
                            print('input error, try again')
                    else:
                        break


        elif op == '2':
            while True:
                print(search_help)
                op = input()

                if op == "":
                    break

                try:
                    res = DM.semantic_search(op, 'page')
                except Exception as e:
                    print("An error occurred:", e.__class__.__name__)

                print('Open the document with the corresponding ID and go to the corresponding page.')
                op = input()

                try:
                    # file_path_with_page = '{}#page={}'.format(paths[int(op)], page_ids[int(op)])
                    # print(file_path_with_page)
                    # win32api.ShellExecute(0, 'open', file_path_with_page, '', '', 1)
                    select = res[int(op)]
                    print('open')
                    print(select)
                    name = select['name']
                    win32api.ShellExecute(0, 'open', os.path.join(args.doc_dir, name), '', '', 1)
                except Exception as e:
                    print("An error occurred:", e.__class__.__name__)

                while True:
                    print('''Manually add semantic tags and attributes, multiple tags can be separated by commas, and the specific format is as follows:
* Add semantic tags: add_tag xxx,xxx
* Delete semantic tags: del_tag xxx,xxx
* Add attributes: add_att xxx,xxx
* Delete attributes: del_att xxx,xxx
Press Enter to return.''')
                
                    op = input()

                    act = op.split(' ')

                    if len(act) > 1:
                        act_type = act[0]
                        tag_att = act[1].replace(' ', '').split(',')

                        if act_type == 'add_tag':
                            DM.add_semantic_tag(name, tag_att)
                            print('Added successfully.')
                            break
                        elif act_type == 'del_tag':
                            DM.del_semantic_tag(name, tag_att)
                            print('Added successfully.')
                            break
                        elif act_type == 'add_att':
                            DM.add_attribute(name, tag_att)
                            print('Added successfully.')
                            break
                        elif act_type == 'del_att':
                            DM.del_attribute(name, tag_att)
                            print('Added successfully.')
                            break
                        else:
                            print('input error, try again')
                    else:
                        break
                    
        elif op == '3':
            DM.update_doc()
        elif op == '4':
            DM.create_semantic_tag()

if __name__ == '__main__':
    main()
