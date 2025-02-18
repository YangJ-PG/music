# -*- coding: utf-8 -*-
"""
    <https://www.hifini.com/>

    * 功能：
        1.自动顺序翻页
        2.自定义 - 列表起始页
        3.自定义 - 内页

    *注意事项：
        @config.ini
        crawler1.1.6
        1.导航下标：首页:0 华语:1 以此类推
        2.导航下标建议对上号 方便文件保存到相应的专辑下
        3.开关值: On:开启/Off:关闭
        4.自定义链接可用于搜索链接,自定义链接为空时默认导航初始链接
        5.结束页>起始页,结束页等于0时默认获取到最后一页  
        6.两个开关不能同时开启 否则默认执行前一个任务
        7.两个开关中任一开启则优先执行 同时关闭时,默认自动顺序下载
        8.默认自动顺序 及 自定义 - 起始列表页  任务执行中关闭,再执行会从最近读取的页码开始读取
        9.文件热度值：自定义 - 内页不生效
        10.页面排序规则：回帖时间:1  发帖时间:2
        11.下载情况追踪及明细 查看'文件日志'

    :copyright: (c) 23:25 05-08-2023  by YangJ.
"""
import configparser
import requests
from bs4 import BeautifulSoup
import datetime
import re
import os
import time
import traceback

class main:

    def __init__(self):
        # 目标网站
        self.domain_url = "https://www.hifini.com/"

        config = configparser.ConfigParser()
        config.read('config.ini', encoding='UTF-8')

        # 抓取的导航下标
        carwler_index = int(config.get('DEFAULT', 'carwler_index').strip())

        # 自定义起始列表页
        diy_outer_run = config.get('DEFAULT', 'diy_outer_run').strip()   # 开关
        diy_page_begin = int(config.get('DEFAULT', 'diy_page_begin').strip())  # 第n页开始
        diy_page_end = config.get('DEFAULT', 'diy_page_end').strip()  # 第n页结束
        diy_outer_link_url = config.get('DEFAULT', 'diy_outer_link_url').strip()  # 自定义链接

        # 自定义内页
        diy_inner_run = config.get('DEFAULT', 'diy_inner_run').strip()  # 开关
        diy_inner_link_url = config.get('DEFAULT', 'diy_inner_link_url').strip()   # 内页地址

        diy_outer_run, \
        diy_outer_link_run, diy_outer_link_url, diy_page_begin, diy_page_end, \
        diy_inner_run, \
        diy_str, diy_less_str = diy_re_justify(diy_outer_run=diy_outer_run,
                                               diy_outer_link_url=diy_outer_link_url,
                                               diy_page_begin=diy_page_begin,
                                               diy_page_end=diy_page_end,
                                               diy_inner_run=diy_inner_run)

        # 文件热度值 - 评论条数下线
        self.comment_min_num = int(config.get('DEFAULT', 'comment_min_num').strip())
        if diy_inner_run:
            self.comment_min_num = 0

        # 文件热度值 - 收听次数下线
        self.listen_min_num = int(config.get('DEFAULT', 'listen_min_num').strip())
        if diy_inner_run:
            self.listen_min_num = 0

        # 页面数据排序规则 - 回帖时间: lastpid  发帖时间: tid
        sort_order = int(config.get('DEFAULT', 'sort_order').strip())
        if sort_order == 1:
            sort_items = {'item': 'lastpid', 'desc': '回帖时间'}
        else:
            sort_items = {'item': 'tid', 'desc': '发帖时间'}

        # 文件日志目录
        self.log_dir = "文件日志"

        # 存储文件父目录
        save_file_parent_dir = "下载文件"

        # 初始化文件日志名称
        self.log_name = self.log_dir+'/carwler_error{}.txt'.format(diy_str)

        try:
            # 获取网站导航栏数据
            response = request_data(page_url=self.domain_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            ul = soup.find('ul', {'class': ['navbar-nav', 'mr-auto']})  # 获取标签
            a_list = ul.find_all('a', {'class': 'nav-link'})  # 获取子标签
            link = link_name = ''
            if carwler_index > len(a_list) - 1:
                carwler_index = len(a_list) - 1

            for index, item in enumerate(a_list):
                if index == carwler_index:
                    link = item['href'].strip()
                    link_name = item.get_text().strip()
                    # 首页
                    if item['href'] == '.':
                        link = 'index'
                    break

            if link == '' or link_name == '':
                self.log_str = get_cur_time() + " 首页导航栏获取失败 "
                self.write_log(page_begin_state=True)
            else:
                # 文件日志名称
                if diy_outer_run:
                    if diy_outer_link_run:
                        self.log_name = self.log_dir + '/crawler_{}({}-{}-{}).txt'.format(link_name, diy_less_str,  diy_page_begin, diy_page_end)
                    else:
                        self.log_name = self.log_dir + '/crawler_{}({}-{}-{}-{}).txt'.format(link_name, diy_less_str, sort_items['desc'], diy_page_begin, diy_page_end)
                elif diy_inner_run:
                    self.log_name = self.log_dir + '/crawler_{}({}).txt'.format(link_name, diy_less_str)
                else:
                    self.log_name = self.log_dir + '/crawler_{}({}).txt'.format(link_name, sort_items['desc'])

                # 文件存储子目录
                self.save_file_dir = save_file_parent_dir + "/" + link_name + '{}/'.format(diy_str)

                # 判断存储文件父目录是否存在
                if not os.path.exists(save_file_parent_dir):
                    encoded_dir_name = save_file_parent_dir.encode('utf-8')  # 将目录名称编码为 utf-8
                    os.makedirs(encoded_dir_name)

                # 判断文件目录是否存在
                if not os.path.exists(self.save_file_dir):
                    encoded_dir_name = self.save_file_dir.encode('utf-8')  # 将目录名称编码为 utf-8
                    os.makedirs(encoded_dir_name)

                if diy_inner_run:
                    fun_state = self.analysis_file(diy_inner_link_url)
                    if fun_state:
                        self.log_str = get_cur_time() + " 获取完毕"
                        self.write_log()
                else:
                    self.log_str = get_cur_time() + " 开始抓取导航栏第{}栏{} ".format(carwler_index + 1, diy_str)
                    self.write_log(page_begin_state=True)

                    page_url_template = self.domain_url + link + "-{}.htm?orderby=" + sort_items['item']
                    # 目标页面 - 获取总页码条目
                    page_end = 0
                    if diy_outer_run:
                        page_end = diy_page_end
                        if diy_outer_link_run:
                            page_url_template = diy_outer_link_url

                    page_end_switch = True
                    if page_end == 0:
                        try:
                            response = request_data(page_url=page_url_template.format(1))
                            repsonse.raise_for_status()
                            soup = BeautifulSoup(response.text, 'html.parser')
                            ul = soup.find('ul', {'class': 'pagination'})  # 获取标签
                            li_list = ul.find_all('li', {'class': 'page-item'})  # 获取子标签
                            if li_list:
                                last_li = li_list[-1]  # 获取最后一个标签
                                last_li_content = last_li.get_text().strip()  # 获取标签内容
                                if last_li_content == '▶':
                                    last_li = li_list[-2]  # 获取倒数二个标签
                                page_end = int(re.sub(r"[^0-9]", "", last_li.get_text().strip()))  # 获取标签内容

                            if page_end == 0:
                                page_end_switch = False
                                self.log_str = get_cur_time() + " 总页数获取失败 - {}".format(link_name)
                                self.write_log(page_begin_state=True)
                            else:
                                if diy_outer_run:
                                    self.log_str = get_cur_time() + " 总页数获取成功, 总共{}页 - {}".format(page_end, link_name)
                                    self.write_log()
                                else:
                                    self.log_str = get_cur_time() + " 总页数获取成功, 总共{}页(根据{}排序) - {}".format(page_end,
                                                                                                          sort_items['desc'],
                                                                                                          link_name)
                                    self.write_log()
                        except requests.exceptions.Timeout as te:
                            self.log_str = get_cur_time() + ' 请求超时002 - {}'.format(str(te))
                            self.write_log()
                        except requests.exceptions.HTTPError as he:
                            self.log_str = get_cur_time() + ' HTTP请求错误002 - {}'.format(str(he))
                            self.write_log()
                        except requests.exceptions.ConnectionError as ce:
                            self.log_str = get_cur_time() + ' 连接异常002 - {}'.format(str(ce))
                            self.write_log()
                        except requests.exceptions.RequestException as re:
                            self.log_str = get_cur_time() + ' 请求异常002 - {}'.format(str(re))
                            self.write_log()
                        except Exception as e:
                            self.log_str = get_cur_time() + ' 程序异常002 - {}'.format(str(e))
                            self.write_log()
                    if page_end_switch:
                        # 目标页面 - 开始页码
                        if diy_outer_run:
                            page_begin = diy_page_begin
                        else:
                            page_begin = 1
                        # 文件日志中获取最近抓取的页码
                        if os.path.exists(self.log_name) and os.path.getsize(self.log_name) > 0:
                            with open(self.log_name, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                lines = [line.strip() for line in lines]
                                lines.reverse()

                            # 获取文件日志中最后100行数据
                            last_100_lines = lines[:100]
                            del lines
                            content = '\n'.join(last_100_lines)
                            result = re.search('第(.*)页', content)
                            del content
                            if result:
                                page_begin = int(re.sub(r"[^0-9]", "", result.group(0)))
                                self.log_str = get_cur_time() + " 继续上次第{}页开始抓取 - {}".format(page_begin, link_name)
                                self.write_log()

                        # 目标页面 - 循环获取每一页的链接
                        for cur_page in range(page_begin, page_end + 1):
                            # 构造当前页面的url
                            page_url = page_url_template.format(cur_page)

                            self.log_str = get_cur_time() + " 第{}页 - {}:".format(cur_page, link_name) + page_url
                            self.write_log(page_begin_state=True)

                            try:
                                # 发送请求并获取响应
                                response = request_data(page_url=page_url)
                                response.raise_for_status()

                                # 解析页面内容
                                soup = BeautifulSoup(response.text, 'html.parser')

                                # 查找元素并获取链接list
                                link_elements = soup.select('div.subject>a')

                                for link_element in link_elements:
                                    # 目标页面 - 音频页面url
                                    link_url = self.domain_url + link_element['href'].strip()

                                    self.log_str = get_cur_time() + " --- 音频页面url:" + link_url
                                    self.write_log()

                                    # 解析页面 - 提取文件
                                    fun_state = self.analysis_file(link_url)
                                    if fun_state:
                                        continue
                            except requests.exceptions.Timeout as te:
                                self.log_str = get_cur_time() + ' 请求超时003 - {}'.format(str(te))
                                self.write_log()
                            except requests.exceptions.HTTPError as he:
                                self.log_str = get_cur_time() + ' HTTP请求错误003 - {}'.format(str(he))
                                self.write_log()
                            except requests.exceptions.ConnectionError as ce:
                                self.log_str = get_cur_time() + ' 连接异常003 - {}'.format(str(ce))
                                self.write_log()
                            except requests.exceptions.RequestException as re:
                                self.log_str = get_cur_time() + ' 请求异常003 - {}'.format(str(re))
                                self.write_log()
                            except Exception as e:
                                self.log_str = get_cur_time() + ' 程序异常003 - {}'.format(str(e))
                                self.write_log()
                        self.log_str = get_cur_time() + " 获取完毕"
                        self.write_log()
        except requests.exceptions.Timeout as te:
            self.log_str = get_cur_time() + ' 请求超时001 - {}'.format(str(te))
            self.write_log()
        except requests.exceptions.HTTPError as he:
            self.log_str = get_cur_time() + ' HTTP请求错误001 - {}'.format(str(he))
            self.write_log()
        except requests.exceptions.ConnectionError as ce:
            self.log_str = get_cur_time() + ' 连接异常001 - {}'.format(str(ce))
            self.write_log()
        except requests.exceptions.RequestException as re:
            self.log_str = get_cur_time() + ' 请求异常001 - {}'.format(str(re))
            self.write_log()
        except Exception as e:
            self.log_str = get_cur_time() + ' 程序异常001 - {}'.format(str(e))
            self.write_log()

    # 写入文件日志并输出
    def write_log(cls, page_begin_state: bool = False):
        # 判断文件目录是否存在
        if not os.path.exists(cls.log_dir):
            encoded_dir_name = cls.log_dir.encode('utf-8')  # 将目录名称编码为 utf-8
            os.makedirs(encoded_dir_name)
        # 写入文件日志并输出
        with open(cls.log_name, 'a', encoding='utf-8') as f:
            if page_begin_state:
                f.write('\n' + cls.log_str + '\n')
                print()
            else:
                f.write(cls.log_str + '\n')
        print(cls.log_str)

    # 解析页面 - 提取文件
    def analysis_file(cls, link_url):
        try:
            # 发送请求并获取响应
            response2 = request_data(page_url=link_url)
            response2.raise_for_status()

            # 解析页面内容
            soup = BeautifulSoup(response2.text, 'html.parser')

            # 文件评论条数
            comment_num = 0
            comment_element = soup.select("div.card.card-postlist span.posts")
            for comment in comment_element:
                comment_num = int(comment.text.strip())

            # 文件收听次数
            listen_num = 0
            listen_element = soup.select("div.jan.card.card-thread i.jan-icon-eye-4")
            for listen in listen_element:
                listen_num = int(listen.parent.text.strip())

            # 查找音频元素并获取音频url
            scripts_element = soup.findAll("script")

            #pattern_01 = "get_music.php(.*)[0-9|a-z|A-Z]"  # 音频url - 01
            #pattern_02 = "(?<=')(.*m4a)(?=')"  # 音频url - 02
            pattern_full = "author[\s\S]*url.*'(.*)(?=')"  # 音频url - 匹配所有
            name_pattern = "title.*(?<=')(.*)(?=')"  # 音频名称
            author_pattern = "author.*(?<=')(.*)(?=')"  # 音频歌手

            for script in scripts_element:
                # 判断script标签中是否有内容
                if script.string:
                    #result_01 = re.search(pattern, script.string)
                    #result_02 = re.search(pattern_02, script.string)
                    result_full = re.findall(pattern_full, script.string)
                    if result_full:
                        # 音频url
                        audio_url = result_full[0].strip()
                        # 判断是否的带有域名
                        pattern_domain = re.compile(
                            "^((http://)|(https://))?([a-zA-Z0-9]([a-zA-Z0-9\\-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z]{2,6}(/)"
                        )
                        if re.search(pattern_domain, audio_url) is None:
                            audio_url = cls.domain_url+audio_url

                        # 音频名称
                        name_result = re.findall(name_pattern, script.string)
                        # 音频歌手
                        author_result = re.findall(author_pattern, script.string)
                        # 获取文件名
                        file_name = name_result[0].strip() + ' - ' + author_result[0].strip()

                        cur_time = get_cur_time()
                        cls.log_str = cur_time + " --- 音频url:" + audio_url
                        cls.write_log()

                        if comment_num < cls.comment_min_num:
                            cls.log_str = cur_time + " --- 评论条数:{}, 低于{}, 热度不足, 跳过下载:".format(comment_num,
                                                                                              cls.comment_min_num) + file_name
                            cls.write_log()
                            return False

                        if listen_num < cls.listen_min_num:
                            cls.log_str = cur_time + " --- 收听次数:{}, 低于{}, 热度不足, 跳过下载:".format(listen_num,
                                                                                              cls.listen_min_num) + file_name
                            cls.write_log()
                            return False

                        try:
                            # 发送请求并获取响应
                            audio_response = request_data(page_url=audio_url, allow_type=False)
                            audio_response.raise_for_status()
                            # 非法字符处理：
                            chars_to_replace = ['/', '\\', ':', '*', '"', '<', '>', '|', '?']
                            # 构建转换表
                            translation_table = str.maketrans({char: '' for char in chars_to_replace})
                            # 替换操作
                            file_name = file_name.translate(translation_table)
                            music_name = file_name + '.mp3'
                            file_name = cls.save_file_dir + music_name

                            # 保存文件
                            with open(file_name, 'wb') as audio_file:
                                audio_file.write(audio_response.content)

                            cls.log_str = get_cur_time() + " {} downloaded successfully!(评论条数:{}, 收听次数:{})".format(
                                music_name, comment_num, listen_num)
                            cls.write_log()
                            return True
                        except requests.exceptions.Timeout as te:
                            cls.log_str = get_cur_time() + ' 请求超时005 - {}'.format(str(te))
                            cls.write_log()
                            return False
                        except requests.exceptions.HTTPError as he:
                            cls.log_str = get_cur_time() + ' HTTP请求错误005 - {}'.format(str(he))
                            cls.write_log()
                            return False
                        except requests.exceptions.ConnectionError as ce:
                            cls.log_str = get_cur_time() + ' 连接异常005 - {}'.format(str(ce))
                            cls.write_log()
                            return False
                        except requests.exceptions.RequestException as re:
                            cls.log_str = get_cur_time() + ' 请求异常005 - {}'.format(str(re))
                            cls.write_log()
                            return False
                        except Exception as e:
                            cls.log_str = get_cur_time() + ' 程序异常005 - {}'.format(str(e))
                            cls.write_log()
                            return False
        except requests.exceptions.Timeout as te:
            cls.log_str = get_cur_time() + ' 请求超时004 - {}'.format(str(te))
            cls.write_log()
            return False
        except requests.exceptions.HTTPError as he:
            cls.log_str = get_cur_time() + ' HTTP请求错误004 - {}'.format(str(he))
            cls.write_log()
            return False
        except requests.exceptions.ConnectionError as ce:
            cls.log_str = get_cur_time() + ' 连接异常004 - {}'.format(str(ce))
            cls.write_log()
            return False
        except requests.exceptions.RequestException as re:
            cls.log_str = get_cur_time() + ' 请求异常004 - {}'.format(str(re))
            cls.write_log()
            return False
        except Exception as e:
            cls.log_str = get_cur_time() + ' 程序异常004 - {}'.format(str(e))
            cls.write_log()
            return False


# 获取当前时间
def get_cur_time():
    current_time = datetime.datetime.now()
    return str(current_time.strftime('%Y-%m-%d %H:%M:%S'))


# 自定义数据处理
def diy_re_justify(diy_outer_run,
                   diy_outer_link_url,
                   diy_page_begin,
                   diy_page_end,
                   diy_inner_run):
    if diy_outer_run == 'On':
        diy_outer_run = True
    else:
        diy_outer_run = False

    if diy_inner_run == 'On':
        diy_inner_run = True
    else:
        diy_inner_run = False

    if diy_outer_run and diy_inner_run:
        diy_inner_run = False

    diy_str = diy_less_str = ''
    diy_outer_link_run = False
    if diy_outer_run:
        if len(diy_page_end) > 0:
            diy_page_end = int(diy_page_end)
            if diy_page_begin > diy_page_end:
                diy_page_end = diy_page_begin
        else:
            diy_page_end = 0

        if len(diy_outer_link_url) > 0:
            diy_outer_link_run = True
            if diy_outer_link_url.endswith('-1.htm'):
                diy_outer_link_url = diy_outer_link_url[:-4] + '-{}.htm'
            elif diy_outer_link_url.endswith('-1.html'):
                diy_outer_link_url = diy_outer_link_url[:-5] + '-{}.html'
            elif diy_outer_link_url.endswith('.htm'):
                diy_outer_link_url = diy_outer_link_url[:-4] + '-1-{}' + diy_outer_link_url[-4:]
            elif diy_outer_link_url.endswith('.html'):
                diy_outer_link_url = diy_outer_link_url[:-5] + '-1-{}' + diy_outer_link_url[-5:]

        if diy_outer_link_run:
            response2 = request_data(page_url=diy_outer_link_url)
            soup = BeautifulSoup(response2.text, 'html.parser')
            seo_element = soup.select("input.form-control")
            # 搜索内容
            for seo_value in seo_element:
                tip = seo_value['value'].strip()
            diy_str = "(搜索列表：{})".format(tip)
            diy_less_str = "搜索列表：{}".format(tip)
        else:
            diy_str = "(自定义列表)"
            diy_less_str = "自定义列表"

    if diy_inner_run:
        diy_str = "(自定义内页)"
        diy_less_str = "自定义内页"

    return diy_outer_run, \
           diy_outer_link_run, diy_outer_link_url, diy_page_begin, diy_page_end, \
           diy_inner_run, \
           diy_str, diy_less_str


# 请求网站数据
def request_data(page_url,
                 allow_type=True,
                 verify=False,
                 timeout=30,
                 headers={"user-agent": "Mizilla/5.0"},
                 allow_redirects=False):
    if allow_type:
        response = requests.get(page_url,
                                timeout=timeout,
                                headers=headers,
                                allow_redirects=allow_redirects)
    else:
        response = requests.get(page_url,
                                timeout=timeout,
                                headers=headers)
    return response


if __name__ == "__main__":
    main()
    # 程序窗口延时关闭
    time.sleep(24*60*60)
