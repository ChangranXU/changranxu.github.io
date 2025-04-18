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

from scholarly import scholarly, ProxyGenerator
import jsonpickle
import json
from datetime import datetime
import os

# 启用 Headless 模式的代理
pg = ProxyGenerator()
if pg.FreeProxies():  # 成功设置免费代理并启用 headless 模式
    scholarly.use_proxy(pg)
else:
    print("⚠️ Failed to set proxy. scholarly may not work in headless mode.")

# 搜索并获取作者信息
try:
    author: dict = scholarly.search_author_id("4_KIgHkAAAAJ")
    scholarly.fill(author, sections=['basics', 'indices', 'counts', 'publications'])

    # 添加时间戳、重构 publication 为字典
    name = author['name']
    author['updated'] = str(datetime.now())
    author['publications'] = {v['author_pub_id']: v for v in author['publications']}

    # 打印输出并保存 JSON 数据
    print(json.dumps(author, indent=2))
    os.makedirs('../assets/results', exist_ok=True)
    with open(f'../assets/results/gs_data.json', 'w') as outfile:
        json.dump(author, outfile, ensure_ascii=False)

    # 生成 shields.io 格式
    shieldio_data = {
        "schemaVersion": 1,
        "label": "citations",
        "message": f"{author['citedby']}",
    }
    with open(f'../assets/results/gs_data_shieldsio.json', 'w') as outfile:
        json.dump(shieldio_data, outfile, ensure_ascii=False)

except Exception as e:
    print("❌ Error occurred while fetching scholar data:")
    print(e)
