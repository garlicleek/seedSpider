import os
import re
from time import sleep

import scrapy
from bs4 import BeautifulSoup
from scrapy import Request

from seedSpider import items

name_list = ['pzdq','xiaomai','yumi','guacai','mianhua','shulei','shuidao','tanglei','mianhua','zaliang','youliao','guoshu','huahui','yaocai','miaomu','malei','mucao']

class BasicSpider(scrapy.Spider):
    name = 'basic'
    allowed_domains = ['www.chinaseed114.com']
    init_url = 'https://www.chinaseed114.com/seed/pzdq/'
    start_urls = []
    offset = 0

    # 方案: 共 534 页 每个元素 页眉 有分类, 根据页眉分成一类. 第三个往后是类型, 由于没有构建关系必要, 把属性存到list,
    # 用 "in" 判断存入 csv
    def start_requests(self):
        # 534
        for name in name_list:
            for i in range(1, 600):
                self.start_urls.append('https://www.chinaseed114.com/seed/{}/{}.html'.format(name,str(i)))
        for start_url in self.start_urls:
            yield Request(url=start_url, callback=self.raw_parse,
                          dont_filter=True)  # Request url must be str or unicode

    def raw_parse(self, response):
        urls = []
        x = response.xpath(r"//li[@class='t_c']//a/@href")
        for selector in x:
            urls.append(selector.get())

        for url in urls:
            yield Request(url=url, callback=self.parse, dont_filter=True)
        # url = 'https://www.chinaseed114.com/seed/14/seed_65428.html'
        # yield Request(url=url, callback=self.parse, dont_filter=True)

    def parse(self, response):
        soup = BeautifulSoup(response.text, 'lxml')
        item = items.SeedspiderItem()
        # 杂粮后面有空格
        item['url'] = response.url
        item['name'] = response.xpath(r"//h1[@class='title']/text()").get()
        # 有的类型写在品种名里
        item['attribute'] = [item['name']]
        attributes = response.xpath(r"//div[@class='pos']/a/text()")
        # print(attributes)
        for attribute in attributes:
            item['attribute'].append(re.sub(r'[\s]', '', attribute.get()))
        # 获取所有文本用正则解决, 返回每个关键词的位置
        item['content'] = {"url": response.url, "其他": "", "特征特性": "", "品种名称": ""}
        temp = re.sub(r"[\xa0]|<[^>]*>", " ", response.xpath(r"//div[@class='content']").get())
        item['content'] = get_attributes(temp, item['content'])
        # 有的名称不一致, 有的作物分类在'品种名称','作物种类'栏
        if item['content']['品种名称'] != 'None':
            item['attribute'].append(item['content']['品种名称'])
        del item['content']['作物种类']
        # 但是 csv 内需要标准的名称
        item['content'].update({"品种名称": item['name']})

        print(item)
        self.offset += 1
        print(self.offset // 80, self.offset % 80, self.offset, item['name'])
        yield item


# 处理用:分割的特征特性
def char_split_2(str):
    attributes = []
    # 处理字符串
    rev_str = str[::-1]
    res = re.finditer("：", rev_str)
    colon = []
    for x in res:
        colon.append(x.start())
    print(colon)
    period = [0]
    for i in range(2):
        try:
            period.append(rev_str.find('。', colon[i]))
        except IndexError:
            # 说明不是用冒号分割, 改用其他方法.
            attributes = char_split(str)
            return attributes
    period.append(len(rev_str))
    # print(period)
    for i in range(len(period) - 1):
        attributes.append(rev_str[period[i]:period[i + 1]][::-1])

    return attributes


atr = {
    "品种名称": ['[品种实验作物]名称'],
    "审定编号": ['[编证]号'],
    "申请单位": ['(引.?进.?|育.?种.?|选.?育.?|申.?请.?)(人|者|公司|单位)', '报审', '申报'],
    "品种来源": ['来源', '亲本'],
    "作物种类": ['作物种类', '品种名称'],
    "特征特性": ['特[性征]', '..性状', '简介'],
    "产量表现": ['产量', '试验表现'],
    "栽培技术要点": ['(栽培|制种).*(技术|要点)'],
    "审定意见": ['意见', '审定情况', '品审会', ],
    "适宜栽培区域": ['适[宜应].{0,4}(地区|区域|范围)'],
    "其他": ["联.?系", "电.?话", "邮.?箱", "邮.?编", "传.?真", "注意事项"],
}


def get_attributes(string, item=None):
    if item is None:
        item = {}
    pos_tmp = {}
    pos = {}
    res = item
    # 找到相应匹配的位置, 便成字典, 按值排序
    for key, values in atr.items():
        x = len(string) + 1
        for value in values:
            tar = re.search(value, string)
            if tar:
                # 匹配位置尽量往前,从而包括更多的内容
                x = min(tar.span()[0], x)
        # 没找到赋值 -1
        if x == len(string) + 1:
            x = -1
        pos_tmp.update({key: x})
    pos_tmp = sorted(pos_tmp.items(), key=lambda t: t[1])
    print(pos_tmp)
    # 以匹配位置为基础, 分别找到左右边界, 从而确定上一个属性结束的地方 和 本属性开始的地方
    # start_list用来保存下一个属性的起始位置
    start_list = []
    # ptr是用来标记前一个元素结束的位置
    ptr = 0
    for key, value in pos_tmp:
        # 如果没有匹配(-1) 以当立即更新为(-1,-1)后立即结束
        if value == -1:
            pos.update({key: (-1, -1)})
            continue
        # 如果有匹配: 先向前寻找左边界
        start = re.search(r'.*[。\s\x0a]', string[ptr:value][::-1])
        print(start)
        if start is not None:
            start = max(value - start.span()[1] + 1, 0)
        else:
            start = ptr
        # 向后寻找右边界
        end = re.search(r'[，。：\s\x0a]+', string[value:])
        print(end)
        if end is not None:
            end = value + end.span()[1]
        else:
            end = start

        pos.update({key: (start, end)})
        print(key, start, end, string[start:end])
        ptr = end
        #
        start_list.append(start)
    # 把第一个元素的开头去掉, 那么整个列表前移一位, 就能够表示后一项的起始位置了
    start_list.remove(start_list[0])
    # 以本属性位置为开始, 下一个属性为结尾
    print(pos)
    print(start_list)
    ptr = 0
    flag = False
    for key, value in pos.items():
        if flag:
            res.update({key: re.sub(r"\s*", "", string[value[1]:len(string)])})
            break
        # 如果没有匹配(-1,-1)应当更新为 标志 None, ptr不变
        if value[0] == -1:
            res.update({key: 'None'})
            continue
        # 如果有匹配那么 把去除空格的字符串[本属性末尾:下一个属性开头]作为值,
        res.update({key: re.sub(r"\s*", "", string[value[1]:start_list[ptr]])})
        print(key,value[0],value[1],start_list[ptr])
        ptr += 1
        if ptr == len(start_list):
            flag = True
    # 抗病 和 品质 的 特殊处理
    res_tmp = char_split(res['特征特性'])
    if res_tmp[1]:
        res.update({"抗病表现": "".join(res_tmp[1])})
    else:
        res.update({"抗病表现": "None"})
    if res_tmp[0]:
        res.update({"品质分析": "".join(res_tmp[0])})
    else:
        res.update({ "品质分析": "None"})
    # 申请单位 的 特殊处理, 申请者掐头, 育种者全删
    new_val = re.sub(r"请(人|者|公司|单位)[，。：\s\x0a]|(选育|育种)(人|者|公司|单位)[，。：\s\x0a].*", "", res['申请单位'])
    res.update({"申请单位": new_val})
    # print(res)
    return res


analyse_list = ['抗性鉴定结果：', '抗病性鉴定，', '抗病性鉴定：', '抗病性接种鉴定，', '抗病性接种鉴定结果：', '接种抗病鉴定结果：', '抗病性鉴定结果：', '抗病性：', '抗病鉴定：',
                '抗性鉴定',
                '抗性鉴定：', '抗病鉴定', '抗性表现：', '抗性：', '抗性评价：', '稻瘟病抗性：', '品种稻瘟病抗性：', '经抗病性鉴定：', '抗性鉴定结论：', '病虫害发生情况', '抗性',
                '病虫发生情况：', '综合抗性', '抗旱鉴定：',
                '抗病评价：', '抗旱鉴定', '抗性分析：', '抗病性鉴定', '抗病抗倒：', '抗病虫性：', '病虫害发生情况：', '田间病虫害发生情况：', '抗倒性强：', '抗病性好：',
                '抗性鉴定结论',
                '抗病评价', '抗虫鉴定', '抗杂棉11A2', '抗虫鉴定：', '品质及抗性', '石抗', '抗病性', '品质及抗性：', '抗病鉴定:', ]
anti_list = ['品质分析结果：', '食用品质：', '品质分析结论:', '品质检验结论：', '品质化验结论', '主要品质指标', '纤维品质：', '纤维品质', '品质混合样测定，', '品质混合样测定，',
             '品质检测，', '测定混合样：', '品质测定结果分别为：', '测试结果平均：', '混合样测定：', '测定，', '检测：', '测试：', '品质分析：', '品质分析', '品质结果：',
             '品质表现：', '品质：', '品质结果', '品质主要指标', '品质化验结论：', '品质检测：', '米质主要指标：', '经品质检测：', '品质', '品质主要指标：']


# 从特征特性中获取抗病和品质分析
def char_split(str):
    le = []
    ld = []
    # str = str.replace(';', '。')
    str = str.split('。')
    # str = str.split()
    for var in str:
        if get_charater(analyse_list, var):
            le.append(get_charater(analyse_list, var))
        elif re.findall(".*稳定时间", var) or re.findall('.*蛋白', var) or re.findall('.*淀粉', var):
            var += '。'
            le.append(var)
        if get_charater(anti_list, var):
            if var.__contains__('；'):
                var = var.split('；')[0]
                var += '。'
                ld.append(var)
            else:
                ld.append(get_charater(anti_list, var))
        elif re.findall(".*病", var):
            if var.__contains__('。'):
                pass
            else:
                var += '。'
            ld.append(var)
    return le, ld


# 从特征特性中获取抗病和品质分析,进行re规则匹配的函数
def get_charater(list, var):
    for t in list:
        ana_str = ".*{}(.*)"
        ana_str = ana_str.format(t)
        # print(ana_str)
        if re.findall(ana_str, var):
            var += '。'
            # print(var.split(t)[1])
            return var.split(t)[1]
