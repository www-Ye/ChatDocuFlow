# Document/Paper Management System based on OpenAI API/ChatGPT

This is a document/paper management system that allows users to add all PDFs in a folder and index them using OpenAI's embedding technology. Users can retrieve documents through natural language search or tags. After selecting a document/paper, they can engage in question-answering to learn more about the paper.

Current include:

* Automatic storage of papers in the database from a folder (papers are automatically divided into chunks, summarized and embedded, and then a summary and embedding for the entire paper is obtained)

* Natural language similarity search for papers (query=[xxx])

* question-answering after entering the paper (questions are answered chunk by chunk and then summarized)

To be added:

* Semantic tags (newly added papers are automatically added to semantically similar tags)

* Regular tags (manually added and will not automatically include semantically similar papers)

* Chunk-level question-answering (directly using natural language dialogue to locate the corresponding chunk in the article and engage in question-answering)

### Configuration

To set up the system, first create a new Conda environment using the following command:

```
conda create --name chatdocuflow python=3.8
conda activate chatdocuflow
```

Next, install the required dependencies:

```
conda install -c pytorch faiss-cpu
pip install -r requirements.txt
```

Start the system by running:

```python main.py --openai_key xxx --language English```

Replace xxx with your OpenAI API key and replace the parameter after "language" with the desired language.

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

这是一个文档/论文管理系统，允许用户添加文件夹中的所有PDF，并使用OpenAI的嵌入技术对其进行索引。用户可以通过自然语言搜索或者标签来检索文档。在选中文档/论文后可以进行对话式问答以了解有关论文的问题。

目前包含功能：

* 自动将文件夹中论文存入数据库（自动将论文分成块，并对每一块总结并嵌入，最后获得一个整篇文章的总结和嵌入）

* 自然语言相似度搜索论文（query=[xxx]）

* 进入论文后可以进行对话式问答，（通过每一块回答问题最后合并总结）

将要加入：

* 语义标签（自动将新增论文添加入语义相似的标签）

* 普通标签（手动添加，不会自动加入语义相似的论文）

* 文本块级问答（直接通过自然语言对话定位到对应文章的块，并进行问答）

### 配置

要设置系统，首先使用以下命令创建一个新的Conda环境：

```
conda create --name chatdocuflow python=3.8
conda activate doc_chatdocuflow
```

接下来，安装所需的依赖项：

```
conda install -c pytorch faiss-cpu
pip install -r requirements.txt
```

通过运行以下命令启动系统：

```python main.py --openai_key xxx --language Chinese```

将 xxx 替换为您的OpenAI API密钥，language 后参数替换为所需的语言。

### 使用

要使用系统，只需将您的PDF文件添加到指定的文件夹中，并等待它们被索引。然后，使用搜索功能查找您需要的文档。您还可以向文档添加标签以帮助组织和检索。

### 贡献

欢迎贡献！如果您有任何建议或改进意见，请随时打开问题或拉取请求。
