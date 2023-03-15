# Document/Paper Management System based on OpenAI API/ChatGPT

This is a document/paper management system that allows users to add all PDF files in a folder and index them using OpenAI's embedding technology. Users can retrieve documents by querying keywords or tags. After selecting a document/paper, conversational question-answering can be conducted to learn about the paper.

The project plans to implement question-answering for all pages in the future.

### Configuration

To set up the system, first download the Neo4j database. Then create a new Conda environment using the following commands:

```
conda create --name doc_manager
conda activate doc_manager
```

Next, install the required dependencies:

```
conda install -c pytorch faiss-cpu
pip install -r requirements.txt
```

Finally, start the Neo4j server by running the following command:

```neo4j.bat console```

Then, start the system by running:

```python main.py --user neo4j --password neo4j --openai_key xxx --language Chinese```

Replace xxx with your OpenAI API key, and Chinese with the desired language for summarization.

### Usage

To use the system, simply add your PDF files to the designated folder, and wait for them to be indexed. Then, use the search functionality to find the documents you need. You can also add tags to the documents to help with organization and retrieval.

### Contributing

Contributions are welcome! Please feel free to open issues or pull requests if you have any suggestions or improvements to make.

### Figure

![alt text](fig/fig1.png)

![alt text](fig/fig2.png)

![alt text](fig/fig3.png)

![alt text](fig/fig4.png)

![alt text](fig/fig5.png)

![alt text](fig/fig6.png)

# 基于OpenAI API/ChatGPT的文档/论文管理系统

这是一个文档/论文管理系统，允许用户添加文件夹中的所有PDF，并使用OpenAI的嵌入技术对其进行索引。用户可以通过查询关键字或标签来检索文档。在选中文档/论文后可以进行对话式问答以了解有关论文的问题。

项目未来打算实现针对所有页面的问答。

### 配置

要设置系统，请首先下载Neo4j数据库。然后使用以下命令创建一个新的Conda环境：

```
conda create --name doc_manager
conda activate doc_manager
```

接下来，安装所需的依赖项：

```
conda install -c pytorch faiss-cpu
pip install -r requirements.txt
```

最后，通过运行以下命令启动Neo4j服务器：

```neo4j.bat console```

然后，通过运行以下命令启动系统：

```python main.py --user neo4j --password neo4j --openai_key xxx --language Chinese```

将 xxx 替换为您的OpenAI API密钥，Chinese 替换为所需的摘要语言。

### 使用

要使用系统，只需将您的PDF文件添加到指定的文件夹中，并等待它们被索引。然后，使用搜索功能查找您需要的文档。您还可以向文档添加标签以帮助组织和检索。

### 贡献

欢迎贡献！如果您有任何建议或改进意见，请随时打开问题或拉取请求。
