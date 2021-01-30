# PornHub-Downloader

基于 `Selenium`  的PornHub视频下载工具，效率一般，用于练手。



## 原理

P站视频的信息包含在视频页面 HTML 中定义的一个 `flashvars` 开头的变量中：

![](./images/flashvars.png)

下载链接包含在这个`videoUrl`中：

![](./images/videoUrl.png)



### 为什么不用 Requests

因为我菜。

打开 `videoUrl` 需要一个名为 `bs` 的 cookie，但是我闹了半天也没解决，非常奇怪。如果之后解决了会更新在这里。



## 环境需求

- Python 3.6+
- tqdm: 用于显示下载进度条
- requests: 用于下载视频
- bs4: 用于解析HTML
- selenium: 用于控制虚拟浏览器



## 使用方法

1. 下载和本地 Chrome 版本对应的 [chromedriver](https://chromedriver.chromium.org/)，放置在环境变量的路径中或者在脚本中指定路径

2. 运行脚本

   ```shell
   $ python pornhub_downloader.py -u https://cn.pornhub.com/view_video.php?viewkey=xxxxxxxxxx -s './学习资料'
   ```

   - -u: 指定你感兴趣的学习资料页面
   - -s: 视频保存的路径，若省略，则在当前路径下的 Download 文件夹（若不存在则自动新建）

