import os
import re
import json
from tqdm import tqdm
import argparse
import requests
import asyncio
import aiohttp
from pyppeteer import launch
from bs4 import BeautifulSoup


async def fetch(session, url, dst, pbar=None, headers=None):
    try:
        if headers:
            async with session.get(url, headers=headers) as resp:
                with(open(dst, 'ab')) as f:
                    while True:
                        chunk = await resp.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        pbar.update(1024)
                pbar.close()
        else:
            async with session.get(url) as resp:
                return resp
    except Exception as e:
        print(e)


async def download_from_url(url, dst):
    async with aiohttp.ClientSession() as session:
        resp = await fetch(session, url, dst)
        file_size = int(resp.headers['content-length'])
        if os.path.exists(dst):
            first_byte = os.path.getsize(dst)
        else:
            first_byte = 0
        if first_byte >= file_size:
            return file_size
        header = {"Range": f"bytes={first_byte}-{file_size}"}
        pbar = tqdm(
            total=file_size, initial=first_byte,
            unit='B', unit_scale=True, desc=dst.rsplit('/', 1)[1])
        await fetch(session, url, dst, pbar=pbar, headers=header)


async def get_single_video(save_path, url, sem):
    async with sem:
        page = await browser.newPage()
        await page.goto(url)
        bs = BeautifulSoup(await page.content(), 'html.parser')

        video_name = bs.find('span', class_="inlineFree").text  # 解析得到视频名称
        script = bs.find('div', class_='original mainPlayerDiv').find('script').string
        script = script.strip()
        var_name = re.findall('var flashvars_(.*) =', script)[0]   # 用正则表达式提取 flashvars 变量名

        js = f"""
        () => {{
        var playerObjList = {{}}
        {script}
        var num = flashvars_{var_name}['mediaDefinitions'].length - 1
        while (flashvars_{var_name}['mediaDefinitions'][num]['format'] != "mp4")
        {{
            num -= 1
        }}
        return flashvars_{var_name}['mediaDefinitions'][num]['videoUrl']
        }}
        """
        video_urls = await page.evaluate(js)   # 执行这段JS代码
        await page.goto(video_urls)
        bs = BeautifulSoup(await page.content(), 'html.parser')
        data = json.loads(bs.text)
        download_url = data[-1]['videoUrl']  # 选择最高清的版本
        await download_from_url(download_url, f'{save_path}/{video_name}.mp4')


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str, help="The video's website url")
    parser.add_argument("-s", "--save-path", help="The save path on your PC", default='./Downloads')
    parser.add_argument("-n", "--num-proc", type=int, help="The number of semaphore", default=5)
    args = parser.parse_args()

    global browser
    browser = await launch(headless=True)
    sem = asyncio.Semaphore(args.num_proc)
    try:
        if 'model' in args.url:   # 下载该 model 的全部视频
            if args.url.endswith('videos'):
                url = args.url
            else:
                url = args.url + '/videos'

            resp = requests.get(url)
            bs = BeautifulSoup(resp.text, 'html.parser')
            name = bs.find('h1', itemprop="name").text.strip()
            urls = ['https://cn.pornhub.com' + a['href'] for a in bs.find('ul', id='mostRecentVideosSection').find_all('a')]
            urls = sorted(set(urls), key=urls.index)
            print(f'开始下载 {name} 的视频，共 {len(urls)} 个')
            save_path = os.path.join(args.save_path, name)
            os.makedirs(save_path, exist_ok=True)

            tasks = [asyncio.create_task(get_single_video(save_path, url, sem)) for url in urls]
            await asyncio.wait(tasks)
        else:  # 下载单个视频
            await get_single_video(args.save_path, args.url, sem)
    finally:
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
    # asyncio.get_event_loop().run_until_complete(main())