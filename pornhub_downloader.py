import os
import re
import json
from tqdm import tqdm # 显示下载进度条
import argparse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def download_from_url(url, save_path):
    response = requests.get(url, stream=True) 
    file_size = int(response.headers['content-length']) 
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
    req = requests.get(url, headers=header, stream=True) 
    with(open(save_path, 'ab')) as f:
        for chunk in req.iter_content(chunk_size=1024): 
            if chunk:
                f.write(chunk)
                pbar.update(1024)
    pbar.close()
    return file_size


def pornhub_downloader(driver, url, save_path):
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
    download_from_url(download_url, os.path.join(save_path, data[-1]['quality']+'P'+'_'+video_name+'.mp4'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", help="The video's website url")
    parser.add_argument("-s", "--save_path", help="The save path on your PC", default='./Download')
    args = parser.parse_args()

    # 创建 Download 文件夹📁
    os.makedirs(args.save_path, exist_ok=True)

    # 开启 headless 浏览器🌍
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(options=chrome_options)
    pornhub_downloader(driver, args.url, args.save_path)
