import sqlite3

class Sqlite_DB:
    def __init__(self, db_name):
        self.db_name = db_name

        self.open()
        self.create_table('docs_table', {"source": "TEXT", "gen_title": "TEXT", "summary": "TEXT", "page_nums": "TEXT", "chunk_nums": "TEXT", "embedding": "BLOB"})
        # self.create_table('pages_table', {"source": "TEXT", "page_id": "TEXT", "page_text": "TEXT", "summary": "TEXT", "embedding": "BLOB"})
        self.create_table('chunks_table', {"source": "TEXT", "page_span": "TEXT", "chunk_id": "TEXT", "chunk_text": "TEXT", "summary": "TEXT", "embedding": "BLOB"})
        self.create_table('semantic_tags_table', {"tag": "TEXT", "embedding": "BLOB"})
        self.create_table('regular_tags_table', {"tag": "TEXT", "embedding": "BLOB"})
        self.create_table('semantic_tags2source_table', {"tag": "TEXT", "source": "TEXT"})
        self.create_table('regular_tags2source_table', {"tag": "TEXT", "source": "TEXT"})
        self.close()

    def create_table(self, table_name, columns):
        columns_str = ', '.join([f"{col_name} {col_type}" for col_name, col_type in columns.items()])
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str});")
        self.conn.commit()

    def insert(self, table_name, data):
        columns_str = ', '.join(data.keys())
        values_placeholder = ', '.join(['?' for _ in data.values()])
        values = tuple(data.values())
        self.cursor.execute(f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_placeholder});", values)
        self.conn.commit()

    def search(self, table_name, conditions=None, selected_columns=None):
        selected_columns_str = ', '.join(selected_columns) if selected_columns else '*'
        
        if conditions:
            conditions_str = ' AND '.join([f"{col_name} = ?" for col_name in conditions.keys()])
            values = tuple(conditions.values())
            self.cursor.execute(f"SELECT {selected_columns_str} FROM {table_name} WHERE {conditions_str};", values)
        else:
            self.cursor.execute(f"SELECT {selected_columns_str} FROM {table_name};")
            
        result = self.cursor.fetchall()

        return result

    def delete(self, table_name, conditions):
        conditions_str = ' AND '.join([f"{col_name} = ?" for col_name in conditions.keys()])
        values = tuple(conditions.values())
        self.cursor.execute(f"DELETE FROM {table_name} WHERE {conditions_str};", values)
        self.conn.commit()

    def open(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def close(self):
        self.cursor.close()
        self.conn.close()
