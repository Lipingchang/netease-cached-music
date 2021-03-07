import queue
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException

from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import subprocess
import asyncio
from ichrome import AsyncChrome,AsyncChromeDaemon
from ichrome import Chrome
import time
import threading
import json

class MyChromeDaemon(object):
    root_url = "http://www.baidu.com"
    # user_data_path = "E:\\workspace\\movie_center_ui\\cache\\chromium_cache_80\\user-data"
    # disk_cache_path = "E:\\workspace\\movie_center_ui\\cache\\chromium_cache_80\\disk-cache"
    # chrome_exe_path = "E:\\workspace\\movie_center_ui\\chrome-win-80\\chrome.exe"
    # chrome_driver_path = "E:\\workspace\\movie_center_ui\\selenium_scraper\\chromedriver_800397.exe"
    user_data_path = os.path.abspath("./cache/chromium_cache/user_data")  # 传入abs路径后，才不会和 headless flag 冲突
    disk_cache_path = os.path.abspath("./cache/chromium_cache/disk_cache")
    chrome_exe_path = os.path.abspath("./chrome_win_80/chrome.exe")
    chrome_driver_path = os.path.abspath("./chrome_win_80/chromedriver_800397.exe")
    proxy_server_address = "http://localhost:1080"
    chrome_debug_address = "127.0.0.1"
    chrome_debug_port = 9222
    debug = False

    def __init__(self):
        self.listen_ready = threading.Semaphore(0)
        self.lyric_queue = queue.Queue()
        self.save_next_req2file = queue.Queue()
        self.init()
        self.start_thread(); # 用一个线程去连接 chrome 实例

    def init(self):
        chrome_options=Options()
        chrome_options.add_argument("--headless") #设置chrome浏览器无界面模式
        # chrome_options.add_argument(f"proxy-server={self.proxy_server_address}")
        chrome_options.binary_location = self.chrome_exe_path
        chrome_options.add_argument(f"user-data-dir={self.user_data_path}")
        chrome_options.add_argument(f"disk-cache-dir={self.disk_cache_path}")
        # chrome_options.add_argument("window-size=1000,1000")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument(f"--remote-debugging-address={self.chrome_debug_address}")
        chrome_options.add_argument(f"--remote-debugging-port={self.chrome_debug_port}")

        #建立浏览器实例
        browser = webdriver.Chrome(options=chrome_options, executable_path=self.chrome_driver_path)
        self.browser = browser
        print("2?")
        browser.set_script_timeout(120)
        # 开始请求
        browser.get(self.root_url)
        print("??")

    def start_thread(self):
        def body():
            self.daemon_coro = self.start_listen_req()
            asyncio.run(self.daemon_coro)
        t = threading.Thread(target=body, name="ichrome")
        self.daemon_thread = t
        t.start()

    async def wait_response_filter(self, r):
        if self.debug:
            print(r)
        if ('params' not in r ):
            return False
        url = r["params"]["response"]["url"]
        requestId = r["params"]["requestId"]
        if (url.strip().split("?")[0] == "https://music.163.com/weapi/song/lyric"):
            # print(url)
            # print(response)
            response = await self.tab.get_response(requestId)
            try:
                body = response["result"]["body"]
                body = json.loads(body)
                lyric_str = body["lrc"]["lyric"]
            except:
                self.lyric_queue.put("")
            else:
                self.lyric_queue.put(lyric_str)
        # try:
        #     item = self.save_next_req2file.get_nowait()
        #     print('download:',url)
        # except:
        #     # 没有要求 就继续 continue
        #     pass
        return False

    async def start_listen_req(self):
        async with AsyncChrome() as chrome:
            async with chrome.connect_tab(0, auto_close=True) as tab:
                self.tab = tab;
                await tab.set_url(url=self.root_url, timeout_stop_loading=True, timeout=5)
                self.listen_ready.release() # v操作早了 有可能会漏掉几个response
                await tab.wait_response(self.wait_response_filter, lambda r: print('cb:'), timeout=float("inf"))  # 没有设置timeout 阻塞了 长时间不结束 会不会让缓存的request过多？


    def download_pic(self, src, dst_path):
        bytes_str = self.browser.execute_async_script("""
        var callback = arguments[arguments.length -1];
        var src = arguments[arguments.length-2];

        xhr = new XMLHttpRequest()
        xhr.responseType = "arraybuffer"
        xhr.open('GET',src)
        xhr.send()
        xhr.onreadystatechange = () => {
          if (xhr.readyState === XMLHttpRequest.DONE) {
            callback(new Uint8Array(xhr.response))
          }
        }
      """, src)
        raw_data = bytes(list(bytes_str))
        f = open(dst_path, 'wb')  # TODO 用操作系统系统的字符串拼接
        f.write(raw_data)
        f.close()


def headlessTest():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-data-dir=E:\\workspace\\netease-cached-music\\cache\\chromium_cache\\user_data3")
    options.binary_location = "./chrome_win_80/chrome.exe"
    driver = webdriver.Chrome(options=options, executable_path= "./chrome_win_80/chromedriver_800397.exe")
    driver.get("https://www.baidu.com")
    print(driver.page_source)
    driver.quit()


# movie_insert_update(db, browser)
def main():
    daemon = MyChromeDaemon()
    daemon.listen_ready.acquire() # 等待 监听线程开始运行
    #
    daemon.browser.get("https://music.163.com/#/song?id=1804320463")
    print("main done")
    # daemon.daemon_thread.join()



def threadTest():
    # 主进程 会在线程创建后一直存在，直到线程都执行完成，才会退出
    def task1():
        time.sleep(4);
        print("hhh")
    t = threading.Thread(target=task1)
    t.start()
    print('...')

def threadTest2():
    def task1():
        time.sleep(4);
        print("hhh")

    t = threading.Thread(target=task1,)
    t.daemon = True
    t.start()
    print('...')


if __name__ == "__main__":
    headlessTest()
