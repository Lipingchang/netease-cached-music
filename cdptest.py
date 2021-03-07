# import pychrome
import os
import subprocess
import asyncio
# import websockets
from ichrome import AsyncChrome,AsyncChromeDaemon
from ichrome import Chrome
import time


def start_chrome():
    chrome_exe_path = r'E:\workspace\movie_center_ui\chrome-win-80'
    os.chdir(chrome_exe_path)
    os.putenv("GOOGLE_API_KEY", "no")
    os.putenv("GOOGLE_DEFAULT_CLIENT_ID", "no")
    os.putenv("GOOGLE_DEFAULT_CLIENT_SECRET", "no")
    with subprocess.Popen(['./chrome.exe','--remote-debugging-port=9223']) as proc:
        print(proc.poll())
        time.sleep(3)
        proc.terminate()
    # env={
                #     "GOOGLE_API_KEY": "no",
                #     "GOOGLE_DEFAULT_CLIENT_ID": "no",
                #     "GOOGLE_DEFAULT_CLIENT_SECRET":"no",
                # }
                 # 同步命令

async def async_operate_tab():
    chrome = AsyncChrome(host='127.0.0.1', port=9223)
    print('init chrome done')

    if not await chrome.connect():
        raise Exception("chrome ws can't connect!")
    print(await chrome.close_browser())

    tab = (await chrome.tabs())

    print(tab)
    async with tab():
        await tab.set_url("http://httpbin.org", timeout=3)
        js_result = await tab.js("document.title")
        print(js_result)

        async def callback_function(request):
            if request:
                for _ in range(3):
                    response = await tab.get_response(request)
                    if response.get('error'):
                        await tab.wait_loading(1)
                        continue
                    print(response)

        def filter_func(r):
            # url = r['params']['response']['url']
            print('filter', r, )
            # print('received:',url)
            return False
            # return url == 'https://github.com/'

        while True:
            task = asyncio.ensure_future(
                tab.wait_response(
                    filter_function=filter_func,
                    callback_function=callback_function,
                ),
            )
            await task

# asyncio.run(async_operate_tab())

# browser = pychrome.Browser(
#     url="http://127.0.0.1:9222"
# )
#
# tab = browser.new_tab()
# tab.start()
# tab.Network.enable()
# browser.

async def main():
    async with AsyncChromeDaemon(
        chrome_path=r"E:\workspace\movie_center_ui\chrome-win-80\chrome.exe",
        user_data_dir=r"E:\workspace\movie_center_ui\cache\chromium_cache_80\user-data",
        debug=True,

    ):
        async with AsyncChrome() as chrome:
            # chrome 打开时会自动开一个tab 连接上他 然后使用他
            # 不然每次都要显示没有正确退出
            async with chrome.connect_tab(0, auto_close=True) as tab:
                print(await tab.url)
                await tab.set_url(url="https://www.baidu.com", timeout_stop_loading=True, timeout=5)
                await tab.wait_request(lambda r: print(r), lambda r: print('cb:'))       # 没有设置timeout 阻塞了


            # async with chrome.connect_tab(index="https://www.baidu.com", auto_close=True) as tab:
            #     print('5-0',time.time())
            #     await tab.wait_loading(5)   # 最长等待网页加载5s
            #     print('5-5',time.time())
            #     await tab.js("")
            #     await asyncio.sleep(1)
            #     print('5-1',time.time())
            #     await tab.wait_request(filter_function=lambda r: print(r), timeout=5)   # 最长等5s
            #     print('5-2', time.time())

            # await chrome.close_browser()

async def runAnother():
    '''
        先用 chromedriver 开一个chrome
        然后 再连 它的 调试接口 监听流量信息
    :return:
    '''


    async with AsyncChrome() as chrome:
        async with chrome.connect_tab(0, auto_close=True) as tab:
            print(await tab.url)
            await tab.set_url(url="https://www.baidu.com", timeout_stop_loading=True, timeout=5)
            await tab.wait_request(lambda r: print(r), lambda r: print('cb:'))  # 没有设置timeout 阻塞了

if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.run(runAnother())
