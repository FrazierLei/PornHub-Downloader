import os
import re
import json
import argparse
import requests
from bs4 import BeautifulSoup
import ffmpy3
from multiprocessing.dummy import Pool as ThreadPool


def ffmpeg_downloader(url, save_path):
    """
    用 ffmpeg 下载并保存
    :param url: m3u8 文件的地址
    :param save_path: 视频保存的位置
    :return: None
    """
    ffmpy3.FFmpeg(inputs={url: None}, outputs={save_path: None}).run()


def pornhub_parser(sess, url):
    """
    解析得到指定 url 的视频对应的 m3u8 文件的地址
    :param sess: 会话
    :param url: 视频或者 model 主页的 url
    :return: (tuple) (m3u8 文件的地址, 视频文件名)
    """
    resp = sess.get(url)
    bs = BeautifulSoup(resp.text, 'html.parser')

    # 解析得到视频名称
    video_name = bs.find('span', class_="inlineFree").text
    script = bs.find('div', class_='original mainPlayerDiv').find('script').string
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
    console.log(flashvars_{var_name}['mediaDefinitions'][num]['videoUrl'])
    """

    # 将这段 JS 代码保存在本地，然后用 node 执行
    with open('pornhub.js', 'w') as f:
        f.write(js)

    video_urls = os.popen('node pornhub.js').read()
    resp = sess.get(video_urls)
    bs = BeautifulSoup(resp.text, 'html.parser')
    data = json.loads(bs.text)

    # 选择最高清的版本
    download_url = data[0]['videoUrl']

    # 删除 JS 文件
    os.remove('pornhub.js')

    # 下载
    print(f"分辨率{data[0]['quality']}P的 m3u8 文件下载地址为：{download_url}")
    # os.popen(f"ffmpeg -i '{download_url}'  -c copy '{filename}'")
    return download_url, video_name + '.mp4'
    

if __name__ == '__main__':
    # 设置代理变量
    os.environ["http_proxy"] = "http://127.0.0.1:7890"
    os.environ["https_proxy"] = "http://127.0.0.1:7890" 

    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str, help="The video's website url")
    parser.add_argument("-s", "--save_path", help="The save path on your PC", default='./Downloads')
    parser.add_argument("-n", "--num_proc", type=int, help="The number of processes", default='1')
    args = parser.parse_args()

    # 创建 Download 文件夹📁
    os.makedirs(args.save_path, exist_ok=True)

    # 初始化 session
    sess = requests.Session()

    # 下载该 model 的全部视频
    if 'model' in args.url:
        # 如果主页连接没有包含 videos，就加上
        if args.url.endswith('videos'):
            url = args.url
        else:
            url = args.url + '/videos'

        resp = requests.get(url)
        bs = BeautifulSoup(resp.text, 'html.parser')
        name = bs.find('h1', itemprop="name").text.strip()
        video_urls = [a['href'] for a in bs.find('ul', id='mostRecentVideosSection').find_all('a')]
        video_urls = sorted(set(video_urls), key=video_urls.index)
        print(f'开始下载 {name} 的视频，共 {len(video_urls)} 个。')
        
        model_urls = []
        for i, url in enumerate(video_urls):
            print(f'{i + 1}.', end=' ')
            url = 'https://cn.pornhub.com' + url
            save_path = os.path.join(args.save_path, name)
            os.makedirs(save_path, exist_ok=True)
            download_url, video_name = pornhub_parser(sess, url)
            save_path = os.path.join(args.save_path, name, video_name) 
            model_urls.append([download_url, save_path])

        # 开 n 个线程池
        pool = ThreadPool(args.num_proc)
        results = pool.starmap(ffmpeg_downloader, model_urls)
        pool.close()
        pool.join()
    
    # 下载单个视频
    else:
        download_url, video_name = pornhub_parser(sess, args.url)
        save_path = os.path.join(args.save_path, video_name) 
        ffmpeg_downloader(download_url, save_path)
