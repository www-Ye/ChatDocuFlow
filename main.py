from doc_management import Doc_Management
import argparse
import time
import os

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--doc_dir", default="documents", type=str)
    parser.add_argument("--db_type", default="neo4j", type=str)
    parser.add_argument("--user", default="neo4j", type=str)
    parser.add_argument("--password", default="neo4j", type=str)
    parser.add_argument("--db_name", default="", type=str)
    parser.add_argument("--language", default="Chinese", type=str)
    parser.add_argument("--doc_range_distance", default=0.5, type=float, help="The doc retrieval threshold returns higher similarity for closer distances.")
    parser.add_argument("--page_range_distance", default=0.4, type=float, help="The page retrieval threshold returns higher similarity for closer distances.")

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
                print('tags:', DM.tag_list)
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
            print('Create tags separated by commas (,), and they will be automatically added to nodes within the threshold distance.')
            op = input()
            tags = op.split(',')
            DM.add_tags(None, tags)

        elif op == '4':
            DM.update_doc()

if __name__ == '__main__':
    main()
