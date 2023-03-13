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
                print(DM.search_help)
                op = input()
                if op == "":
                    break
                DM.search(op, 'doc')

        elif op == '2':
            while True:
                print(DM.search_help)
                op = input()
                if op == "":
                    break
                DM.search(op, 'page')

        elif op == '3':
            DM.update_doc()

        elif op == '4':
            DM.create_semantic_tag()

if __name__ == '__main__':
    main()
