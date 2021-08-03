import os
import re
import json
from tqdm import tqdm # 显示下载进度条
import argparse
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def download_from_url(url, save_path, proxies=None):
    resp = requests.get(url, stream=True, proxies=proxies) 
    file_size = int(resp.headers['content-length']) 
    if os.path.exists(save_path):
        first_byte = os.path.getsize(save_path) 
    else:
        first_byte = 0
    if first_byte >= file_size: 
        return file_size
    header = {"Range": f"bytes={first_byte}-{file_size}"} 
    pbar = tqdm(
        total=file_size, initial=first_byte,
        unit='B', unit_scale=True, desc=save_path)
    resp = requests.get(url, headers=header, stream=True, proxies=proxies) 
    with(open(save_path, 'ab')) as f:
        for chunk in resp.iter_content(chunk_size=1024): 
            if chunk:
                f.write(chunk)
                pbar.update(1024)
    pbar.close()
    return file_size


def pornhub_downloader(driver, url, save_path, proxies):
    driver.get(url)
    bs = BeautifulSoup(driver.page_source, 'html.parser')

    # 解析得到视频名称
    video_name = bs.find('span', class_="inlineFree").text
    script = bs.find('div',class_='original mainPlayerDiv').find('script').string
    script = script.strip('\n').strip('\t')

    # 用正则表达式提取 flashvars 变量名
    var_name = re.findall('var flashvars_(.*) =', script)[0]

    # 执行这段 JS 代码
    js = f"""
    var playerObjList = {{}}
    {script}
    var num = flashvars_{var_name}['mediaDefinitions'].length - 1
    while (flashvars_{var_name}['mediaDefinitions'][num]['format'] != "mp4")
    {{
        num -= 1
    }}
    return flashvars_{var_name}['mediaDefinitions'][num]['videoUrl']
    """

    # 测试时将这段 JS 代码保存在本地，方便 Debug
    # with open('pornhub.js', 'w') as f:
    #     f.write(js)

    video_urls = driver.execute_script(js)  
    driver.get(video_urls)
    bs = BeautifulSoup(driver.page_source, 'html.parser')
    data = json.loads(bs.text)

    # 选择最高清的版本
    download_url = data[-1]['videoUrl']

    # 下载
    print(f"分辨率{data[-1]['quality']}P的下载地址为：{download_url}")
    download_from_url(download_url, os.path.join(save_path, data[-1]['quality']+'P'+'_'+video_name+'.mp4'), proxies)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str, help="The video's website url")
    parser.add_argument("-s", "--save_path", help="The save path on your PC", default='./Downloads')
    args = parser.parse_args()

    # 目前从真实地址下载不需要代理，但是下载速度会受到限制
    proxies = {
        'http': 'http://127.0.0.1:7890',
        'https': 'http://127.0.0.1:7890',
    }

    # 创建 Download 文件夹📁
    os.makedirs(args.save_path, exist_ok=True)

    # 开启 headless 浏览器🌍
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(options=chrome_options)

    # 下载该 model 的全部视频
    if 'model' in args.url:
        if not args.url.endswith('videos'):
            url = urljoin(args.url+'/', 'videos')
        else:
            url = args.url
        resp = requests.get(url)
        bs = BeautifulSoup(resp.text, 'html.parser')
        name = bs.find('h1', itemprop="name").text.strip()
        video_urls = [a['href'] for a in bs.find('ul', id='mostRecentVideosSection').find_all('a')]
        video_urls = sorted(set(video_urls),key=video_urls.index)
        print(f'开始下载 {name} 的视频，共 {len(video_urls)} 个。')
        
        for i, url in enumerate(video_urls):
            print(f'{i}.', end=' ')
            url = 'https://cn.pornhub.com' + url
            save_path = os.path.join(args.save_path, name)
            os.makedirs(save_path, exist_ok=True)
            pornhub_downloader(driver, url, save_path, proxies)
    
    # 下载单个视频
    else:
        pornhub_downloader(driver, args.url, args.save_path, proxies)        
