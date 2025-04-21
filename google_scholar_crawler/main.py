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
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError

def fill_author_with_timeout(author, timeout=120):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(scholarly.fill, author, sections=['basics', 'indices', 'counts', 'publications'])
        return future.result(timeout=timeout)

# 获取作者基本信息
author = scholarly.search_author_id("4_KIgHkAAAAJ")

try:
    author = fill_author_with_timeout(author, timeout=120)
except TimeoutError:
    print("Timeout: scholarly.fill took too long.")
    exit(1)

name = author['name']
author['updated'] = str(datetime.now())
author['publications'] = {v['author_pub_id']: v for v in author['publications']}

# 输出 JSON
print(json.dumps(author, indent=2))

# 保存 JSON 文件
os.makedirs('../assets/results', exist_ok=True)
with open(f'../assets/results/gs_data.json', 'w') as outfile:
    json.dump(author, outfile, ensure_ascii=False)

# 保存 citation badge 数据
shieldio_data = {
    "schemaVersion": 1,
    "label": "citations",
    "message": f"{author['citedby']}",
}
with open(f'../assets/results/gs_data_shieldsio.json', 'w') as outfile:
    json.dump(shieldio_data, outfile, ensure_ascii=False)
