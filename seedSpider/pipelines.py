# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import csv
import json
import os
import re

import pandas

# 柚子属于柑橘类水果
crop = {
    "shuidao": ["水稻"],
    "yumi": ["玉米"],
    "xiaomai": ["小麦"],
    "malingshu": ["马铃薯"],
    "mianhua": ["棉花"],
    "dadou": ["大豆"],
    "gaoliang": ["高粱"],
    "youcai": ["油菜"],
    "huasheng": ["花生"],
    "baicai": ["白菜"],
    "ganlan": ["甘蓝"],
    "huanggua": ["黄瓜"],
    "lajiao": ["辣椒"],
    "fanqie": ["番茄"],
    "qiezi": ["茄子"],
    "xigua": ["西瓜"],
    "tiangua": ["甜瓜"],
    "xihulu": ["西葫芦"],
    "pingguo": ["苹果"],
    "li": ["梨"],
    "putao": ["葡萄"],
    "tao": ["桃"],
    "ganju": ["柑", "橘", "柚"],
    "caomei": ["草莓"],
    "ganzhe": ["甘蔗"]
}


# 不为空的控制一般为与其他属性写在了一起

class SeedspiderPipeline:
    path = os.getcwd() + '/data'
    csvpath = path + '/csv'
    txtpath = path + '/txt'
    header = ['url', '品种名称', '审定编号', '申请单位', '品种来源', '特征特性', '产量表现', '栽培技术要点', '审定意见', '适宜栽培区域', '抗病表现', '品质分析', '其他']

    def __init__(self):
        if not os.path.exists(self.csvpath):
            os.makedirs(self.csvpath)
        if not os.path.exists(self.txtpath):
            os.makedirs(self.txtpath)

    def __del__(self):
        # 在爬虫结束后删除所有csv文件的重复行
        for parent, dirnames, filenames in os.walk(self.csvpath):
            for filename in filenames:
                file_path = os.path.join(parent, filename)  # 得到文件的绝对/相对路径
                data = pandas.read_csv(file_path)
                data.drop_duplicates(inplace=True)
                data.to_csv(file_path, encoding='utf8', index=None)

    def process_item(self, item, spider):  # filenotfound # mkdir 系统找不到指定的路径
        # 25种生成csv, 其他的生成txt备用
        print("processing item...")
        find = False
        for name in item['attribute']:
            for key, patterns in crop.items():
                for pattern in patterns:
                    if re.search(pattern, name):
                        filename = self.csvpath + '/' + key + '.csv'
                        # 文件不存在就写个开头
                        if not os.path.isfile(filename):
                            with open(filename, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=self.header)
                                writer.writeheader()
                        # 追加写
                        with open(filename, 'a', encoding='utf-8', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=self.header)
                            writer.writerow(item['content'])
                        find = True
                        break
                if find:
                    break
            if find:
                break

        filename = self.txtpath
        for name in item['attribute']:
            filename += '/' + name
        if not os.path.exists(filename):
            os.makedirs(filename)
        filename += '/' + item['name'] + '.json'
        with open(filename, "w", encoding='utf-8') as f:
            lines = json.dumps(dict(item), ensure_ascii=False) + '\n'
            f.write(lines)

        return item
