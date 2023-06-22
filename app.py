from flask import Flask, render_template, jsonify, request
import config
import json
import openai

from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.prompts.prompt import PromptTemplate
# Memory
from langchain.memory import ConversationBufferMemory
from langchain.memory import ConversationBufferWindowMemory
import re

import os
os.environ["OPENAI_API_KEY"] = "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"

def page_not_found(e):
  return render_template('404.html'), 404

app = Flask(__name__)
app.config.from_object(config.config['development'])
app.register_error_handler(404, page_not_found)

#########    対話型鑑賞の処理内容    ######## 

llm = ChatOpenAI(model_name="gpt-3.5-turbo")
    # ファシリテータ
facilitator_prompt = PromptTemplate(
  input_variables=["history","input"],
  template="""
  あなたはファシリテーター、私は鑑賞者です。
  鑑賞者が提示する作品について鑑賞者と対話型鑑賞をしてくだvtsさい。
  ファシシテータは鑑賞者の意見を引き出すよう努めてください。

  {history}
  鑑賞者:{input}
  ファシリテーター:
  """
)
memory = ConversationBufferMemory(ai_prefix="ファシリテーター",human_prefix="鑑賞者") #memoryとしてインスタンスを作っている、初期化
conversation = ConversationChain(
  llm=llm, 
  memory=memory,  
  prompt=facilitator_prompt,
  )

#ファシリテーターの評価(assesment)
assesment_prompt = PromptTemplate(
    input_variables=["input","history"],
    template="""
    過去の改善案：{history}
    現状の対話型鑑賞をしているファシリテーターの発言を以下の項目に基づいて省みてください。
    
    受け答え:直前の鑑賞者の言葉に対して反応しているか
    言い換え:直前の鑑賞者の言葉に対して反応しつつ、それをにた言葉で言い換えているか
    結びつけ:直前の鑑賞者の言葉に対して、2つ以上前の鑑賞者の言葉を1つ引き出し、対比させているか
    まとめ:2つ以上前の鑑賞者の言葉を複数引き出し、鑑賞の中で出てきた事柄について筋道立てて整理できているか
    焦点化:作品の中で注目する場所、話すべき話題を絞ることを提案できているか
    
    その後、ファシリテータに対する具体的な改善案も提示してください。
    
    鑑賞者とファシリテータの対話は以下のような内容で行われています。
    {input}
    改善案:
    """
)
asses_memory = ConversationBufferWindowMemory(k=1)
assesment = ConversationChain(
    llm=llm,
    memory=asses_memory,
    prompt=assesment_prompt,
)

#改善したファシリテータ
re_facilitator_prompt = PromptTemplate(
   input_variables=["history","input"],
    template="""
    以下の改善案を受けて発言を修正して、もう一度鑑賞者に問いかけてください。
    改善案:{input}
    {history}
    ファシリテーター:
    """ 
)
re_conversation = ConversationChain(
    llm=llm,
    memory=memory,
    prompt=re_facilitator_prompt,
)


#########    Flaskの処理内容    ######## 
@app.route('/', methods = ['POST', 'GET'])
def index():
  if request.method == 'POST':
    
      #### 鑑賞者のテキスト処理 ####
      prompt = request.form['prompt']
      res = {}
      memo = memory.load_memory_variables({})
      
      if not memo["history"]:
        try:
          res['answer'] = conversation.predict(input=prompt)
        except:
          res['answer'] = "ごめんさい"
          
      else: 
        #これまでの会話の履歴を取得
        conversation.predict(input=prompt)
        memo = memory.load_memory_variables({})
        memo["history"]
        #一連の会話をもとに改善案を生成
        assesment.predict(input=memo["history"])
        #改善案のうち、必要のない部分を削除
        memo_asses = asses_memory.load_memory_variables({})
        m = memo_asses["history"] #改善案の中身
        improvemant = re.search(r'AI:(.*)',m,re.DOTALL)
        improvemant = improvemant.group(1).strip("\n")
        try:
          res['answer'] = re_conversation.predict(input=improvemant)
        except:
          res['answer'] = "ごめんさい"
      
      history = memory.load_memory_variables({})
      with open("./vtsgpt_git/vts_history.json","w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
      return jsonify(res),200 #json形式でgptの返答を保存している
    
  return render_template('index.html', **locals())


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='8888', debug=True)
