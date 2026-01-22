from ollama import generate
import re
import json
import os

os.environ["PATH"] += r";C:\Users\user\AppData\Local\Programs\Ollama"

'''texts = [
    "我已經準備了洋蔥、胡蘿蔔和馬鈴薯，接下來可以做什麼？",
    "我把雞胸肉和大蒜切好了，有什麼料理可以做？",
    "冰箱裡有番茄、青椒和洋蔥，我想做晚餐，有什麼建議？",
    "我已經把麵團揉好了，下一步該怎麼做？",
    "蛋糕麵糊已經攪拌均勻，下一步是什麼？",
    "蔬菜都切好了，下一步應該放進鍋裡炒還是煮？",
    "我手上有雞蛋、牛奶和麵粉，可以做什麼甜點？",
    "冰箱裡有豆腐和青菜，能做什麼中式料理？",
    "有豬肉、香菇和白菜，有什麼適合晚餐的食譜？"
]'''

text1 = "我已經準備了洋蔥、胡蘿蔔和馬鈴薯，接下來可以做什麼？"
text2 = "我把雞胸肉和大蒜切好了，有什麼料理可以做？"
text3 = "冰箱裡有番茄、青椒和洋蔥，我想做晚餐，有什麼建議？"
text4 = "我已經把麵團揉好了，下一步該怎麼做？"
text5 = "蛋糕麵糊已經攪拌均勻，下一步是什麼？"
text6 = "蔬菜都切好了，下一步應該放進鍋裡炒還是煮？"
text7 = "我手上有雞蛋、牛奶和麵粉，可以做什麼甜點？"
text8 = "冰箱裡有豆腐和青菜，能做什麼中式料理？"
text9 = "有豬肉、香菇和白菜，有什麼適合晚餐的食譜？"
text10="請推薦一些適合素食者的中式料理，不要包含豆製品和菇類"

#for i, text in enumerate(texts, start=1):#如果要用迴圈跑多筆測試資料，可以用這行
prompt = f"""
你是一個「嚴格字串抽取器（strict extract-only）」系統。

任務：僅從文字中抽取【明確逐字出現】的實體與關係。

【可抽取的實體類型】
1. 食材：
   - 文字中逐字出現的具體食材名詞
   - 例如：洋蔥、胡蘿蔔、雞胸肉

2. 不喜歡的食材：
   - 使用者明確表達厭惡、不吃、排斥的食材
   -- 僅限以下語意明確的表達：
    【厭惡／不吃】
   - 「不喜歡 X」
   - 「討厭 X」
   - 「不吃 X」
   - 「不想吃 X」

   【明確排除】
   - 「不要 X」
   - 「不要包含 X」
   - 「不包含 X」
   - 「排除 X」

   - X 必須是文字中逐字出現的食材名稱
   - 不得推測或擴展

3. 食譜名稱：
   - 文字中逐字出現的料理名稱

4. 步驟：
   - 文字中逐字出現的操作或烹飪動作
   - 例如：切、揉、攪拌、煮、炒

【關係抽取規則】
1. 只有在文字中同時出現：
   - 「食材 + 食譜名稱」
   才可建立關係：
   {{
     "from": "食材",
     "to": "食譜名稱",
     "relation": "可以做"
   }}

2. 若文字中出現「不喜歡的食材（厭惡或排除）」，必須建立關係：

   - 若使用的語句屬於【厭惡／不吃】：
     （不喜歡 X、討厭 X、不吃 X、不想吃 X）
     則：
     {{
       "from": "使用者",
       "to": "X",
       "relation": "討厭"
     }}

   - 若使用的語句屬於【明確排除】：
     （不要 X、不要包含 X、不包含 X、排除 X）
     則：
     {{
       "from": "使用者",
       "to": "X",
       "relation": "排除"
     }}
     - 若同一排除或厭惡語句中，使用「和」、「以及」、「、」、「&」、「跟」連接多個食材，
       必須將每一個食材分別建立獨立關係 edge。


3. 若無符合條件的關係，edges 必須為空陣列 []

【嚴格規則】
- 不得推測、補齊、概括、改寫原文
- 只允許抽取原文逐字出現的詞
- 若沒有任何符合條件的實體，nodes 輸出 []

=================
【文字】
"{text10}"
=================

【輸出格式（嚴格遵守，不可多字）】
{{
  "nodes": [
    {{ "name": "..." }}
  ],
  "edges": [
    {{
      "from": "...",
      "to": "...",
      "relation": "..."
    }}
  ]
}}

請輸出 JSON：
"""


response = generate(
    model="gemma3:4b",
    system="你是一個 JSON API，只能輸出 JSON，禁止輸出任何說明。",
    prompt=prompt,
    options={"temperature": 0, "top_p": 0}
)

raw = response["response"]

match = re.search(r"\{[\s\S]*\}", raw)
if not match:
    print("test1: 未找到 JSON")
else:
    data = json.loads(match.group(0))

    # 所有節點名稱
    nodes_list = [n["name"] for n in data["nodes"]]

# 建立 edges：只有 from/to 都在 nodes 裡才抓
edges_list = []
for edge in data.get("edges", []):
    from_node = edge.get("from")
    to_node = edge.get("to")
    relation = edge.get("relation")

    if (from_node == "使用者" or from_node in nodes_list) \
       and to_node in nodes_list \
       and relation:
        edges_list.append({
            "from": from_node,
            "to": to_node,
            "relation": relation
        })

# 🔴 print 一定要在 for 迴圈外
print("test1 nodes:", nodes_list)
print("test1 edges:", edges_list)
print("-" * 50)
