# 基于OpenAI API/ChatGPT的文档/论文管理系统

这是一个文档/论文管理系统，允许用户添加文件夹中的所有PDF，并使用OpenAI的嵌入技术对其进行索引。用户可以通过自然语言搜索或者标签来检索文档。在选中文档/论文后可以进行会话问答以了解有关论文的问题。也可以直接检索相似文本块，进行文本块级会话问答。会话功能记住3次交互上下文。
加入了问题重写部分提高了检索的单轮和多轮检索的准确率。

目前包含功能：

* 自动将文件夹中论文存入数据库（自动将论文分成块，并对每一块总结并嵌入，最后获得一个整篇文章的总结和嵌入）

* 自然语言相似度搜索论文（query=[xxx]）

* 进入论文后可以进行会话问答，（通过每一块回答问题最后合并总结）

* 文本块级对话（直接通过自然语言对话定位到对应文章的块，并进行会话问答）

* 文本块级对话的简单可视化界面

将要加入：

* 语义标签（自动将新增论文添加入语义相似的标签）

* 普通标签（手动添加，不会自动加入语义相似的论文）

* 设计更好的prompt

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

通过运行以下命令启动系统(main.py为命令行，app.py为前端)：

```
python main.py --openai_key xxx --language English --system windows
python app.py --openai_key xxx --language English --system windows
```

将 xxx 替换为您的OpenAI API密钥，language 后参数替换为所需的语言。system参数为windows或mac。

### 使用

要使用系统，只需将您的PDF文件添加到指定的文件夹中，并等待它们被索引。然后，使用搜索功能查找您需要的文档。您还可以向文档添加标签以帮助组织和检索。

### 图片

整体架构图

![alt text](fig/chatdocuflow_zh.png)

简单可视化界面

![alt text](fig/gui.png)

初始界面

![alt text](fig/fig1.png)

输入1进入搜索文档界面

![alt text](fig/fig2.png)

查询示例，query=[chatgpt language model]

![alt text](fig/fig3.png)

输入对应id进入文档操作界面

![alt text](fig/fig4.png)

输入3展示对应文档文本块细节

![alt text](fig/fig5.png)

输入1或4进入文档会话模式，进行问答

![alt text](fig/fig6.png)

![alt text](fig/fig7.png)

初始界面输入2进入块级会话

![alt text](fig/fig8.png)

![alt text](fig/fig9.png)

多轮会话

![alt text](fig/fig10.png)

![alt text](fig/fig11.png)

sqlite数据库存储

![alt text](fig/db.png)

### 贡献

欢迎贡献！如果您有任何建议或改进意见，请随时打开问题或拉取请求。