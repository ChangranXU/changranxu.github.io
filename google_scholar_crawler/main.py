# from scholarly import scholarly
# import jsonpickle
# import json
# from datetime import datetime
# import os

# author: dict = scholarly.search_author_id("4_KIgHkAAAAJ")
# scholarly.fill(author, sections=['basics', 'indices', 'counts', 'publications'])
# name = author['name']
# author['updated'] = str(datetime.now())
# author['publications'] = {v['author_pub_id']:v for v in author['publications']}
# print(json.dumps(author, indent=2))
# os.makedirs('../assets/results', exist_ok=True)
# with open(f'../assets/results/gs_data.json', 'w') as outfile:
#     json.dump(author, outfile, ensure_ascii=False)

# shieldio_data = {
#   "schemaVersion": 1,
#   "label": "citations",
#   "message": f"{author['citedby']}",
# }
# with open(f'../assets/results/gs_data_shieldsio.json', 'w') as outfile:
#     json.dump(shieldio_data, outfile, ensure_ascii=False)


from scholarly import scholarly
import json
import jsonpickle
import time
from datetime import datetime
import os

def fetch_author_with_retries(author_id: str,
                              max_retries: int = 3,
                              delay: int = 5) -> dict:
    """
    尝试 fetch 作者信息，失败时最多重试 max_retries 次，每次重试前等待 delay 秒。
    """
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[Attempt {attempt}] Fetching author {author_id} …")
            author = scholarly.search_author_id(author_id)
            # 在 fill 之前也加个小延迟，进一步降低封禁风险
            time.sleep(1)
            scholarly.fill(author, sections=['basics', 'indices', 'counts', 'publications'])
            return author
        except Exception as e:
            print(f"❌ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                print(f"⏳ Waiting {delay}s before retry …")
                time.sleep(delay)
    raise RuntimeError(f"Failed to fetch author {author_id} after {max_retries} attempts")

if __name__ == "__main__":
    # 参数配置
    AUTHOR_ID = "4_KIgHkAAAAJ"
    MAX_RETRIES = 3     # 最多重试次数
    RETRY_DELAY = 5     # 重试间隔（秒）

    # 1. 获取并重试
    author = fetch_author_with_retries(AUTHOR_ID,
                                       max_retries=MAX_RETRIES,
                                       delay=RETRY_DELAY)

    # 2. 后处理：添加更新时间、重构 publications 字典
    author['updated'] = datetime.now().isoformat()
    author['publications'] = {
        v['author_pub_id']: v
        for v in author.get('publications', [])
    }

    # 3. 打印并保存结果
    print(json.dumps(author, indent=2, ensure_ascii=False))

    os.makedirs('../assets/results', exist_ok=True)
    with open('../assets/results/gs_data.json', 'w', encoding='utf-8') as f:
        json.dump(author, f, ensure_ascii=False, indent=2)

    # 4. 生成 shields.io 用的数据
    shieldio_data = {
        "schemaVersion": 1,
        "label": "citations",
        "message": str(author.get('citedby', '0')),
    }
    with open('../assets/results/gs_data_shieldsio.json', 'w', encoding='utf-8') as f:
        json.dump(shieldio_data, f, ensure_ascii=False, indent=2)

    print("✅ Done.")
