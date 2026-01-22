from pypdf import PdfReader #PdfReader：用來讀PDF文件

pdf_path = r"C:\Users\user\Desktop\vs\RAG\ch07.pdf"
reader = PdfReader(pdf_path)

# 選擇要的頁碼
selected_pages = [2, 4]  # 第3頁和第5頁

pages = [reader.pages[i].extract_text() for i in selected_pages]#用 extract_text() 提取文字，存到 pages 列表中

# 印出每個選定頁的文字
for idx, page_text in zip(selected_pages, pages):
    print(f"Page {idx+1}:\n{page_text}\n{'-'*50}")

# chunk，只對選定頁做切分
chunk_size = 500 #每個 chunk 最多 500 個字元
chunks = []
for page_text in pages:
    for i in range(0, len(page_text), chunk_size):
        chunks.append(page_text[i:i+chunk_size])

# 印出所有 chunks
print("結果:")
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}:\n{chunk}\n{'-'*50}")


