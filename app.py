from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from neo4j import GraphDatabase
from ollama import generate
import requests, re, json, os
from starlette.middleware.sessions import SessionMiddleware
from auth import router as auth_router #把auth.py裡的router拿出來，改名叫auth_router

# ------------------- FastAPI & Neo4j -------------------
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="secret123")#加入Session 中介層（middleware）
#提供一個跨request可保存狀態地方與機制，可以用來存使用者名稱、登入資訊
app.include_router(auth_router)#include_router =「把別的檔案裡定義的 API，接到主 FastAPI 上」

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "neo4j123")
)

# ------------------- HTML首頁 -------------------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):#注入Request物件，用來讀session
    username = request.session.get("username")#從session取出登入者名稱
    if not username:
        return RedirectResponse("/")#若未登入，導回首頁（登入頁）

    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    return html.replace("{{username}}", username)


# ------------------- 新增使用者討厭的食物 -------------------
class DislikeRequest(BaseModel):
    ingredient: str

@app.post("/user/dislike")
def add_dislike(request: Request, data: DislikeRequest):
    username = request.session.get("username")
    if not username:
        raise HTTPException(401, "未登入")

    query = """
    MERGE (u:User {id: $user})
    MERGE (i:Ingredient {name: $ingredient})
    MERGE (u)-[:DISLIKES]->(i)
    """

    with driver.session() as session:
        session.execute_write(
            lambda tx: tx.run(query, user=username, ingredient=data.ingredient)
        )#匿名函數（lambda function），tx 代表交易物件，tx.run(...) 執行 Cypher 查詢

    return {"status": "ok"}

# ------------------- TheMealDB 抓食譜 -------------------
def fetch_mealdb_recipe(meal_name: str) -> dict:#-> dict(回傳值型別註解):表示函式會回傳一個 Python 字典（dict
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={meal_name}"
    res = requests.get(url)#發送 HTTP GET 請求
    if res.status_code != 200:
        return {}
    data = res.json()
    if not data.get("meals"):
        return {}
    meal = data["meals"][0]

    ingredients = []
    for i in range(1, 21):
        ing = meal.get(f"strIngredient{i}") #存食材名稱
        measure = meal.get(f"strMeasure{i}") #存食材用量
        if ing and ing.strip(): #若食材名稱存在且非空白，ing.strip()：去掉字串前後空白
            ingredients.append(f"{ing.strip()} ({measure.strip() if measure else ''})")#如果 measure 有值就去掉前後空白。如果 measure 是 None，就用空字串。

    return {
        "recipe_name": meal.get("strMeal", "未知"),
        "ingredients": ingredients,
        "cuisine": meal.get("strArea", "未知"),
        "cooking_method": meal.get("strInstructions", "")
    }

# ------------------- 存食譜到 Neo4j -------------------
def save_recipe_to_graph(data):
    #UNWIND 的作用：把列表拆開，逐個處理
    #要用 WITH 把想保留的變數傳給下一步
    query = """
    MERGE (r:Recipe {name: $name})
    WITH r
    UNWIND $ingredients AS ing
        MERGE (i:Ingredient {name: ing})
        MERGE (r)-[:HAS_INGREDIENT]->(i)
    WITH r
    MERGE (c:Cuisine {name: $cuisine})
    MERGE (r)-[:BELONGS_TO]->(c)
    WITH r
    MERGE (m:Method {name: $method})
    MERGE (r)-[:USES_METHOD]->(m)
    """
    try:
        with driver.session() as session:
            session.execute_write(lambda tx: tx.run(
                query,
                name=data["recipe_name"],
                ingredients=data["ingredients"],
                cuisine=data.get("cuisine", "未知"),
                method=data.get("cooking_method", "未知")
            ))
        print(f"Saved recipe: {data['recipe_name']}")
    except Exception as e:
        print("Neo4j save error:", e)

# ------------------- 背景任務 -------------------
def save_mealdb_recipe_background(meal_name: str):
    recipe = fetch_mealdb_recipe(meal_name)
    if recipe and recipe.get("recipe_name"): #有資料才寫入圖資料庫
        save_recipe_to_graph(recipe)

class MealRequest(BaseModel):
    meal_name: str

@app.post("/recipe_from_mealdb")
def add_recipe_from_mealdb(data: MealRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(save_mealdb_recipe_background, data.meal_name)
    return {"status": "processing", "message": f"食譜 {data.meal_name} 正在存入 Neo4j"}

# ------------------- LLM 抽實體 + Neo4j子圖 -------------------
class TextQueryRequest(BaseModel):
    text: str
    hops: int = 2 #兩跳 A--r1-->B--r2-->C
    limit: int = 50 #最多返回50個節點

class Neo4jSubgraphRetriever:
    def __init__(self, driver):#建構子
        self.driver = driver #把外部傳進來的driver存到物件屬性self.driver，讓這個類別的其他方法都能用它來操作 Neo4j

    def get_subgraph_by_nodes(self, node_names, hops=2, limit=50):
        if not node_names: #node_names是一個列表->要查詢的起始節點名稱
            return []
        #MATCH (n)  整個圖的所有節點
        #WHERE n.name IN $nodes 篩選節點，只留下名稱在 $nodes 列表裡的節點
        #MATCH p = (n)-[*1..{hops}]-(m)  尋找從n出發，長度1到hops 的任意關係路徑
        cypher = f"""
        MATCH (n) 
        WHERE n.name IN $nodes
        WITH n
        MATCH p = (n)-[*1..{hops}]-(m)
        RETURN p
        LIMIT $limit
        """
        with self.driver.session() as session: #with區塊結束時會自動關閉session
            result = session.run(cypher, {"nodes": node_names, "limit": limit})
            return [record["p"] for record in result]
        #變成這樣的意思result = [
            #{"p": "路徑1"},
        #]

retriever = Neo4jSubgraphRetriever(driver)#建立 Neo4jSubgraphRetriever 物件，並把 driver 存到 self.driver

@app.post("/extract_entities")
def extract_entities_and_subgraph(data: TextQueryRequest):
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
"{data.text}"
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

請輸出 JSON:
"""
    # ------------------- 呼叫 Ollama LLM -------------------
    os.environ["PATH"] += r";C:\Users\user\AppData\Local\Programs\Ollama"
    response = generate(
        model="gemma3:4b",
        system="你是一個 JSON API，只能輸出 JSON，禁止輸出任何說明。",
        prompt=prompt,
        options={"temperature": 0, "top_p": 0} #生成方式參數:溫度0、top_p 0，確保不會額外生成文字
    )

    raw = response["response"]
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return {"nodes": [], "edges": [], "subgraph": []}

    # ------------------- 解析 LLM JSON -------------------
    data_json = json.loads(match.group(0))
    node_names = [n["name"] for n in data_json.get("nodes", [])]

    # ------------------- 過濾掉使用者不喜歡 / 排除的食材 -------------------
    exclude_ingredients = {
        edge["to"] for edge in data_json.get("edges", [])
        if edge.get("relation") in ["排除", "討厭"]
    }

    if exclude_ingredients:
        query_exclude = """
        MATCH (r:Recipe)-[:HAS_INGREDIENT]->(i:Ingredient)
        WHERE i.name IN $exclude
        RETURN DISTINCT r.name AS recipe_name
        """
        with driver.session() as session:
            excluded_recipes = [record["recipe_name"] for record in session.run(
                query_exclude, {"exclude": list(exclude_ingredients)}
            )]
        node_names = [n for n in node_names if n not in excluded_recipes]

    # ------------------- 抓子圖 -------------------
    paths = retriever.get_subgraph_by_nodes(node_names, hops=data.hops, limit=data.limit)
    readable_subgraph = []

    for path in paths:
        for rel in path.relationships:
            start = rel.start_node["name"]
            end = rel.end_node["name"]
            relation = rel.type  # 使用 Neo4j 的關係名稱
            readable_subgraph.append(f"{start} → {relation} → {end}") #我改成了我們看得懂的樣子

    # ------------------- 回傳 -------------------
    return {
        "nodes": node_names,
        "edges": data_json.get("edges", []),
        "subgraph": readable_subgraph
    }
