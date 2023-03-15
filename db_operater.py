import pandas as pd
import sqlite3
from py2neo import Graph, Node, Relationship
from py2neo import NodeMatcher, RelationshipMatcher
import numpy as np

class Neo4j_DB:
    def __init__(self, user, password):
        ## Connect to the Neo4j database by entering the user password.
        self.graph = Graph('http://localhost:7474', auth=(user, password))
        # self.graph.delete_all()

        self.node_matcher = NodeMatcher(self.graph)
        self.relationship_matcher = RelationshipMatcher(self.graph)

    def execute_cypher(self, cypher):
        return self.graph.run(cypher)

    def create_relation(self, node1, node2, re_type):
        relation = self.get_relation(node1, node2, re_type).first()
        if relation is None:
            relation = Relationship(node1, re_type, node2)
            self.graph.create(relation)

    def get_relation(self, node1, node2, re_type):
        return self.relationship_matcher.match((node1, node2), r_type=re_type)
    
    def delete_relation(self, node1, node2, re_type):
        relation = self.get_relation(node1, node2, re_type).first()

        self.graph.separate(relation)

    def get_nodes(self, node_type, name=None, page_id=None):

        if name is None:
            nodes = self.node_matcher.match(node_type)
        else:
            if page_id is None:
                nodes = self.node_matcher.match(node_type, name=name)
            else:
                nodes = self.node_matcher.match(node_type, name=name, page_id=page_id)

        return nodes
    
    def create_node(self, node_type, name, embedding=None, summary=None, page_id=None, tags=None, text=None):
        # node = node_matcher.match(e_type).where(node_id=node_id).first()
        node = self.get_nodes(node_type, name, page_id).first()
        if node is None:
            node = Node(node_type, name=name, embedding=embedding, summary=summary, page_id=page_id, tags=tags, text=text)
            self.graph.create(node)

        return node
    
    def delete_node(self, node_type, name):
        nodes = self.get_nodes(node_type, name)

        for node in nodes:
            self.graph.delete(node)


class Sqlite_DB:
    def __init__(self, db_name):
        self.db_name = db_name

    def create_table(self):
        pass

    def open(self):
        # Open database connection.
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def close(self):
        # Close database connection.
        self.cursor.close()
        self.conn.close()