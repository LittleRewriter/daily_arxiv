import datetime
import time
import requests
import json
from datetime import timedelta
from functools import reduce
import xml.etree.ElementTree as ET
import os

isEmpty = True

class arxiv_entry:
    def __init__(self, id: str, pub: str, title: str, abs: str) -> None:
        self.id: str = id
        self.pub: str = pub
        self.title: str = title
        self.abs: str = abs
        
    def sim_id(self) -> str:
        return self.id.split('/')[4].split('v')[0]
    
    def __repr__(self) -> str:
        return f"<{self.sim_id()}|{self.pub}>:{self.title}"

def get_arxiv_result(ent_py: dict,  query_cat: str, max_result: int, date: str):
    get_url = f"https://export.arxiv.org/api/query?search_query=cat:{query_cat}&start=0&max_results={max_result}&sortBy=lastUpdatedDate&sortOrder=descending"
    xml = requests.get(get_url).text
    xml = reduce(lambda x, y: x + "\n" + y, xml.replace(" xmlns=\"http://www.w3.org/2005/Atom\"", "").split("\n")[1:]) 
    tree = ET.fromstring(xml)
    entries = tree.findall("entry")
    for ent in entries:
        id = ent.find("id").text
        pub = ent.find("published").text
        title = ent.find("title").text
        summ = ent.find("summary").text.replace('\n', ' ')
        if pub.find(date) != -1:
            n_entry = arxiv_entry(id, pub, title, summ)
            ent_py[n_entry.sim_id()] = n_entry
    time.sleep(3)
    
    
def get_code(ent_py: dict[str, arxiv_entry]):
    base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"
    cnt = 0

    content: dict[str, str] = dict()
    cnt = 0
    for k,v in ent_py.items():
        url = base_url + k
        if cnt % 10 == 0:
            print(f"get code {cnt+1} / {len(ent_py)}")
        cnt = cnt + 1
        try:
            r = requests.get(url).json()
            if "official" in r and r["official"]:
                cnt += 1
                repo_url = r["official"]["url"]
                repo_name = repo_url.split("/")[-1]
                content[k] = f"[{v.title}]({v.id}), [{repo_name}]({repo_url})\n\n"
            time.sleep(0.1)
        except Exception as e:
            print(f"exception: {e} with id: {k}")
    return content

if __name__ == "__main__":

    DateToday = datetime.date.today()
    # N = 2 # 往前查询的天数
    # data_all = []
    day = str(DateToday + timedelta(-1))
    print(day)
    #     # you can add the categories in cats
    cats = [
        "cs.cv", "cs.gr", "cs.hc", "cs.ai", "physics.comp-ph"
    ]
    res = dict()
    for s in cats:
        get_arxiv_result(res, s, 100, day)
        print(f"cat {s}, sum result {len(res)}")
    fmt_md = get_code(res)
    res_str = ""
    for k, v in fmt_md.items():
        res_str += v
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        if len(fmt_md) == 0:
            json_str = json.dumps("今天是休假喵~")
            f.write(f"content={json_str}")
        else:
            f.write(f"content={json.dumps(res_str)}")