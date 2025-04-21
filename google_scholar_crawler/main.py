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

#!/usr/bin/env python3
"""
Add a 2‑minute hard timeout around the whole Google‑Scholar scraping job.
"""

import signal
from datetime import datetime
import os
import json
import jsonpickle
from scholarly import scholarly

# ---------- 1. 设定超时处理 ----------
class TimeoutException(Exception):
    """Raised when the execution exceeds the given time limit."""
    pass

def _timeout_handler(signum, frame):
    raise TimeoutException("Operation exceeded 120 seconds")

signal.signal(signal.SIGALRM, _timeout_handler)   # 绑定处理器
signal.alarm(120)                                 # **两分钟硬超时**（秒）

# ---------- 2. 主要逻辑 ----------
try:
    author: dict = scholarly.search_author_id("4_KIgHkAAAAJ")
    scholarly.fill(author, sections=['basics', 'indices', 'counts', 'publications'])

    author['updated'] = str(datetime.now())
    author['publications'] = {v['author_pub_id']: v for v in author['publications']}

    print(json.dumps(author, indent=2, ensure_ascii=False))

    os.makedirs('../assets/results', exist_ok=True)
    with open('../assets/results/gs_data.json', 'w') as f:
        json.dump(author, f, ensure_ascii=False, indent=2)

    shieldio_data = {
        "schemaVersion": 1,
        "label": "citations",
        "message": f"{author['citedby']}",
    }
    with open('../assets/results/gs_data_shieldsio.json', 'w') as f:
        json.dump(shieldio_data, f, ensure_ascii=False, indent=2)

except TimeoutException as e:
    print(f"[ERROR] {e} — exiting early.")
except Exception as e:
    print(f"[ERROR] Unexpected exception: {e}")
finally:
    signal.alarm(0)   # 取消定时器，防止影响后续代码
