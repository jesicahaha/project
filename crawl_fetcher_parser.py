import requests #發送HTTP請求->即為爬蟲的點擊，以獲取網頁內容
from bs4 import BeautifulSoup #BeautifulSoup是python的網頁解析工具:將html原始碼轉成「可以搜尋的樹狀結構」

def fetch_html(url: str) -> str: #根據URL獲取網頁HTML內容  #參數: url:str->傳入網址(字串)， ->str ->回傳HTML內容(字串)
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    #User-Agent:模擬瀏覽器行為，避免被網站封鎖 (告訴伺服器你是誰，使用的是什麼裝置/系統/瀏覽器)
    #Moxilla/5.0:通用的User-Agent字串，表示你使用的是一個現代的瀏覽器
    resp.raise_for_status() #檢查請求是否成功(狀態碼200)，若不成功則拋出異常
    return resp.text #回傳網頁HTML內容(字串)

def parse_recipe(html: str, url: str) -> dict: #html:str->從網頁抓下來的html原始碼 url:str->食譜網頁的網址
    #dict → Python 字典，包含食譜資訊
    soup = BeautifulSoup(html, "html.parser") #"html.parser"是python內建解析器
    #用BeautifulSoup把html文字轉成可操作的物件soup
    #soup物件可以用CSS選擇器來搜尋、提取、修改html內容

    title = soup.select_one("h1").text.strip()

    ingredients = [
        i.text.strip()
        for i in soup.select(".ingredient")
    ]

    steps = [
        s.text.strip()
        for s in soup.select(".step")
    ]

    return {
        "title": title,
        "ingredients": ingredients,
        "steps": steps,
        "url": url
    }
