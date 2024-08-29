import datetime
import time
import requests
import json
from datetime import timedelta
from functools import reduce
import xml.etree.ElementTree as ET

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
    
    

# def get_daily_code(DateToday, cats):
#     """
#     @param DateToday: str
#     @param cats: dict
#     @return paper_with_code: dict
#     """
#     global isEmpty
#     from_day = until_day = DateToday
#     content = dict()
#     # content
#     output = dict()
#     for k,v in cats.items():
#         scraper = arxivscraper.Scraper(category=k, date_from=from_day,date_until=until_day)
#         tmp = scraper.scrape()
#         if isinstance(tmp,list):
#             for item in tmp:
#                 if item["id"] not in output:
#                     # print(v, item["categories"], [(x in v) for x in item["categories"]])
#                     if any([(x in item["categories"]) for x in v]):
#                         output[item["id"]] = item
#             isEmpty = False
#         time.sleep(10)
#     base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"
#     cnt = 0

#     for k,v in output.items():
#         _id = v["id"]
#         paper_title = " ".join(v["title"].split())
#         paper_url = v["url"]
#         paper_abs = v["abstract"]
#         url = base_url + _id
#         try:
#             r = requests.get(url).json()
#             if "official" in r and r["official"]:
#                 cnt += 1
#                 repo_url = r["official"]["url"]
#                 repo_name = repo_url.split("/")[-1]
#                 content[_id] = f"[{paper_title}]({paper_url}), {repo_name}\n\n"
#         except Exception as e:
#             print(f"exception: {e} with id: {_id}")
#     return content

# def update_daily_json(filename,data_all):
#     with open(filename,"r") as f:
#         content = f.read()
#         if not content:
#             m = {}
#         else:
#             m = json.loads(content)
    
#     #将datas更新到m中
#     for data in data_all:
#         m.update(data)

#     # save data to daily.json

#     with open(filename,"w") as f:
#         json.dump(m,f)
    



# def json_to_md(filename):
#     """
#     @param filename: str
#     @return None
#     """

#     with open(filename,"r") as f:
#         content = f.read()
#         if not content:
#             data = {}
#         else:
#             data = json.loads(content)
#     # clean README.md if daily already exist else creat it
#     with open("README.md","w+") as f:
#         pass
#     # write data into README.md
#     with open("README.md","a+") as f:
#         # 对data数据排序
#         for day in sorted(data.keys(),reverse=True):
#             day_content = data[day]
#             if not day_content:
#                 continue
#             # the head of each part
#             f.write(f"## {day}\n")
#             f.write("|paper|code|\n" + "|---|---|\n")
#             for k,v in day_content.items():
#                 f.write(v)
    
#     print("finished")        

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
    # data = get_daily_code(day,cats)
    # print(data)
    # res = ""
    # for k, v in data.items():
    #     res += v
    # with open("daily_out.md", "w") as f:
    #     if isEmpty:
    #         f.write("今天是休假喵~")
    #     else:
    #         f.write(json.dumps(res))
    # update_daily_json("daily.json",data_all)
    # json_to_md("daily.json")
    res = dict()
    for s in cats:
        print("get cat", s, ":")
        get_arxiv_result(res, s, 100, day)
    fmt_md = get_code(res)
    res_str = ""
    for k, v in fmt_md.items():
        res_str += v
    with open("daily_out.md", "w") as f:
        if len(fmt_md) == 0:
            f.write("今天是休假喵~")
        else:
            f.write(json.dumps(res_str))