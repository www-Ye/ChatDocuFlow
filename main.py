from doc_management import Doc_Management
import argparse
import time
import os

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--doc_dir", default="docs", type=str)
    parser.add_argument("--db_name", default="docuflow.db", type=str)
    parser.add_argument("--language", default="English", type=str)
    parser.add_argument("--doc_range_distance", default=0.4, type=float, help="The doc retrieval threshold returns higher similarity for closer distances.")
    parser.add_argument("--chunk_range_distance", default=0.3, type=float, help="The chunk retrieval threshold returns higher similarity for closer distances.")

    parser.add_argument("--openai_key", default="", type=str)
    parser.add_argument("--proxy", default="", type=str)

    args = parser.parse_args()
    
    print('*Welcome to Document Management*')

    DM = Doc_Management(args)

    while True:
        if DM.doc_nums == 0:
            print('The paper is missing in the folder. Please add the paper.')
            time.sleep(3)
            break
        
        print(DM.action_help)

        op = input()
        if op == "":
            print('***Thank you for using.***')
            time.sleep(3)
            break

        if op == '1':
            while True:
                print('semantic tags:', DM.semantic_tags_list)
                print('regular tags:', DM.regular_tags_list)
                print(DM.doc_search_help)
                op = input()
                if op == "":
                    break
                DM.search_doc(op, 'doc')

        elif op == '2':
            print('To be added.')
            pass
            # while True:
            #     print('tags:', DM.tag_list)
            #     print(DM.page_search_help)
            #     op = input()
            #     if op == "":
            #         break
            #     DM.search(op, 'page')

        elif op == '3':
            # print('Choose to add semantic tags to documents (input "doc") or pages (input "page").')
            # add_type = input()
            # add or del tag
            print('''Add/Delete semantic tags, automatically connecting with similar papers when adding. The specific format is as follows:
*"add_tag=[xxx,zzz]" represents adding tags.
*"del_tag=[xxx,yyy]" represents deleting tags.

Press Enter to return.''')
            op = input()
            if op == '':
                continue
            
            act = op.split('=')
            if len(act) > 1:
                act_type = act[0]
                try:
                    tags = act[1][1:-1].split(',')
                except Exception as e:
                    print("An error occurred:", e.__class__.__name__)
                    continue
                
                if act_type == 'add_tag':
                    DM.add_tags(None, tags)
                    print('Added successfully.')
                elif act_type == 'del_tag':
                    DM.del_tags(None, tags)
                    print('Deleted successfully.')
                else:
                    print('input error, try again')

        elif op == '4':
            DM.update_doc()

if __name__ == '__main__':
    main()
