#coding : utf-8
import time
import os
import re
import shutil
import sys
import glob
import eyed3
from eyed3.id3.tag import  Tag, ImagesAccessor, LyricsAccessor
from eyed3.id3.frames import ImageFrame
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, LoggingEventHandler
from selenium.webdriver.remote.remote_connection import LOGGER as seleniumLogger
import logging
import filetype
from mutagen.mp4 import MP4
from configparser import ConfigParser

from chrome_Daemon import MyChromeDaemon


class Netease_music:
    def __init__(self, src_dir='', des_dir=''):
        ''' src_dir 保存着被网易云缓存的音乐文件（需要解密）
            des_dir 保存解密后的音乐文件 （带封面 歌词 歌手信息）
        '''

        # 初始化工作文件夹
        self.src_dir = src_dir
        self.des_dir = des_dir
        self.lrc_dir = os.path.join(des_dir, 'lyric') # 缓存下载的歌词文件
        self.cover_dir = os.path.join(des_dir, 'cover') # 缓存歌词封面
        self.msc_dir = os.path.join(des_dir, 'msc')   # 缓存解密的音乐文件
        self.ready_msc_dir = os.path.join(des_dir,'readyMusic')  # 处理完毕的音乐文件
        self.ready_msc_list_file = os.path.join(self.ready_msc_dir,".list.txt")
        logging.info("Current src_dir: %s", src_dir)
        logging.info("Current des_dir: %s", des_dir)

        # 新建目标文件夹
        if not os.path.exists(des_dir):
            os.mkdir(des_dir)
        if not os.path.exists(self.lrc_dir):
            os.mkdir(self.lrc_dir)
        if not os.path.exists(self.msc_dir):
            os.mkdir(self.msc_dir)
        if not os.path.exists(self.cover_dir):
            os.mkdir(self.cover_dir)
        if not os.path.exists(self.ready_msc_dir):
            os.mkdir(self.ready_msc_dir)

        # 找出要转换的加密文件
        os.chdir(src_dir)
        self.uc_files = glob.glob('*.uc') #+ glob.glob('*.uc!') # 找出符合文件名的文件
        self.id_uc_mp = {} # 文件名字和id对应表
        for i in self.uc_files:
            self.id_uc_mp[self.getSongId(i)] = i

    # 从缓存文件名中提取出歌曲的id
    # 缓存文件名字 结构： 156828-128-4e5e8487039537d52d70e2e37ce85682.idx/info/uc
    # uc 音频文件
    # info 格式 音量
    # idx 文件大小 文件已经下载的区间？
    def getSongId(self, name):
        id = name[:name.find('-')]
        logging.debug("getSongId: %s", id)
        return id

    def getInfoFromWeb(self, musicId):
        daemon.browser.get("https://music.163.com/#/song?id=%s" % musicId)
        daemon.browser.switch_to.frame("contentFrame")

        img = daemon.browser.find_element_by_xpath('//body/div[3]/div[1]/div/div/div[1]/div[1]/div[1]/div[1]/img')
        title = daemon.browser.find_element_by_xpath('//body/div[3]/div[1]/div/div/div[1]/div[1]/div[2]/div[1]/div/em')
        artist = daemon.browser.find_elements_by_xpath('//body/div[3]/div[1]/div/div/div[1]/div[1]/div[2]/p[1]/span/a')
        album = None
        try:
            album = daemon.browser.find_element_by_xpath('//body/div[3]/div[1]/div/div/div[1]/div[1]/div[2]/p[2]/a')
        except:
            pass

        imgUrl = img.get_attribute("data-src")
        titleStr = title.get_attribute("innerHTML")
        artistStr = [x.get_attribute("innerHTML") for x in artist]
        artistStr = " / ".join(artistStr)
        if album is None:
            albumStr = ""
        else:
            albumStr = album.get_attribute("innerHTML")
        # lyricStr = daemon.lyric_queue.get(True)
        return [
            imgUrl,
            titleStr,
            artistStr,
            albumStr,
            # lyricStr,
        ]

    def decrypt(self, musicId):
        cachePath = os.path.join(self.src_dir, self.id_uc_mp.get(musicId))
        mscFilePath = os.path.join(self.msc_dir,musicId+'.mp3')
        try:  # from web
            with open(mscFilePath,'wb') as f:
                f.write(bytes(self._decrypt(cachePath)))
        except Exception as e:  # from file
            logging.error("musicId: %s file decrypt fail: %s", musicId, e)
            return None
        logging.debug("musicId: %s file decrypt to %s", musicId, mscFilePath)
        return mscFilePath
            
    def _decrypt(self,cachePath):
        with open(cachePath, 'rb') as f:
            btay = bytearray(f.read())
        for i, j in enumerate(btay):
            btay[i] = j ^ 0xa3
        return btay

    def getAllMusic(self):
        with open(self.ready_msc_list_file, "a+") as file: # 打开记录已经 查找过的歌曲记录 的文件
            file.seek(0)
            alreadyIds = file.readlines() # 读取所有的id
            for _i, musicId in enumerate(self.id_uc_mp):
                logging.info("doing: %s", musicId)
                if musicId+"\n" in alreadyIds: # 已经记录过的
                    continue
                path = self.getMusic_only_text(musicId)
                if path is None:
                    continue;
                else:
                    file.write("%s\n"%musicId)
                    alreadyIds.append("%s\n"%musicId)
            # self._getAllMusic(ids, file)

    # 只向音乐文件中添加 作者等信息 不添加图片节省存储空间
    def getMusic_only_text(self, musicId):
        logging.info("===================================")
        logging.info("开始转存 %s 歌曲", musicId)
        # 破解id对应文件名字的 文件 返回 结果文件路径
        mscFilePath = self.decrypt(musicId) # 把异或后的文件保存到msc文件夹中, 然后开始找tab信息
        logging.info("歌曲 转换成功")
        try:
            info = self.getInfoFromWeb(musicId)
        except Exception as e:
            logging.error("歌曲 %s web加载失败: %s", musicId, e)
            e.with_traceback()
            return None;
        logging.info("歌曲 web 资料获取成功")
        logging.info(f"对文件添加元数据：{mscFilePath}")

        # 识别音频文件格式
        mscFileType = filetype.guess(mscFilePath)
        if mscFileType is None:
            logging.error(f"歌曲文件格式识别失败！{mscFilePath}")
            return None;
    
        mscFileExtension = mscFileType.extension

        if mscFileExtension == 'mp3':
            # 是mp3格式：
            mscFile = eyed3.load(mscFilePath)
            mscFile.tag.album = info[3]
            mscFile.tag.artist = info[2]
            mscFile.tag.title = info[1]
            mscFile.tag.user_text_frames.set("netease_url", musicId)
            mscFile.tag.save(encoding="utf8", version=(2, 3, 0))
        elif mscFileExtension == 'm4a' or mscFileExtension == 'mp4' :
            m4aMscFile = MP4(mscFilePath)
            m4aMscFile.tags['\xa9nam']=info[1]
            m4aMscFile.tags['\xa9ART']=info[2]
            m4aMscFile.tags['\xa9alb']=info[3]
            m4aMscFile.tags['\xa9cmt']=f"netease_url:{musicId}"
            m4aMscFile.save()
            mscFileExtension = 'm4a'
        else:
            logging.error(f"歌曲文件格式:{mscFileExtension},无法添加元数据, 所以没有添加数据")


        # 重命名后移动文件
        mscFileDstPath = os.path.join(self.ready_msc_dir,
                                              "%s - %s.%s" % (re.sub(r"[\/\\\:\*\?\"\<\>\|]", "", info[1]), musicId, mscFileExtension))
        shutil.move(mscFilePath, mscFileDstPath)
        logging.info(f"歌曲保存至指定目录成功{musicId},{mscFileDstPath}")
        return mscFileDstPath

    def getMusic(self, musicId):
        logging.info("开始转存 %s 歌曲", musicId)
        # 破解id对应文件名字的 文件 返回 结果文件路径
        mscFilePath = self.decrypt(musicId) # 把异或后的文件保存到msc文件夹中, 然后开始找tab信息
        logging.info("歌曲 转换成功")
        try:
            info = self.getInfoFromWeb(musicId)
        except Exception as e:
            logging.info("歌曲 %s web加载失败: %s", musicId, e)
            e.with_traceback()
            return None;
        logging.info("歌曲 web 资料获取成功")
        # print(info)
        print(mscFilePath)
        mscFile = eyed3.load(mscFilePath)
        mscFile.tag: Tag;
        mscFile.tag.images: ImagesAccessor
        mscFile.tag.lyrics: LyricsAccessor

        picPath = os.path.join(self.cover_dir, musicId + ".jpg")
        daemon.download_pic(info[0] + "?param=500y500", picPath)  # 下载图片
        imageLoad = open(picPath, "rb").read()
        mscFile.tag.images.set(ImageFrame.FRONT_COVER, imageLoad, "image/jpeg", u"cover_description")
        # imageLoad = open(r"C:\Users\DogEgg\Pictures\Saved Pictures\back_cover.jpg", "rb").read() # 可以放多个图片，iTunes只识别第一张，foobar2000识别多个type的图片 所有的软件对歌手的头像都是联网下载的 不会看tag里面的图片集
        # mscFile.tag.images.set(ImageFrame.LEAD_ARTIST, imageLoad, "image/jpeg", u"artist")
        # mscFile.tag.images.set(ImageFrame.ARTIST, imageLoad, "image/jpeg", u"artist")
        # mscFile.tag.lyrics.set(info[4])
        mscFile.tag.album = info[3]
        mscFile.tag.artist = info[2]
        mscFile.tag.title = info[1]
        mscFile.tag.user_text_frames.set("netease_url", musicId)
        # windows 自带的播放器 Groove音乐 只支持 id3v2.3 格式的, 之前没有指定version 有些文件被保存为 v2.4的，在windows文件夹的预览中，就看不到封面图片了
        mscFile.tag.save(encoding="utf8", version=(2, 3, 0))

        mscFileDstPath = os.path.join(self.ready_msc_dir,
                                              "%s - %s.mp3" % (re.sub(r"[\/\\\:\*\?\"\<\>\|]", "", info[1]), musicId))
        shutil.move(mscFilePath, mscFileDstPath)
        logging.info("歌曲保存至指定目录成功")
        return mscFileDstPath

    def start_dir_watch(self):
        # TODO 没有把触发事件的文件加入 记录文件中
        logging.info("start dir watch")
        observer = Observer()
        event_handler = self.FileModifyHandler(self)
        # event_handler = LoggingEventHandler()
        observer.schedule(event_handler, self.src_dir, recursive=False)
        observer.start()
        return observer

    class FileModifyHandler(FileSystemEventHandler):
        def __init__(self, context):
            super().__init__()
            self.lastModifyFile = None;
            self.context = context
            logging.info('FileModifyHandler init done..')

        def on_modified(self, event: FileSystemEvent):
            if not os.path.basename(event.src_path).endswith("uc"):
                # 只监视uc文件
                return;
            if event.src_path == self.lastModifyFile:
                basename = os.path.basename(event.src_path)
                logging.info("Netease cache file: %s", basename)
                # 此文件修改了两次 说明缓存好了
                songId = self.context.getSongId(basename)
                self.context.id_uc_mp[songId] = event.src_path
                self.context.getMusic_only_text(songId)
            self.lastModifyFile = event.src_path


if __name__ == '__main__':
    config = ConfigParser()
    config.read('./decrypt.config')
    srcDir = config["global"]["srcDir"]
    desDir = config["global"]["desDir"]
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%H:%M:%S')
    seleniumLogger.setLevel(logging.WARNING)
    logging = logging.getLogger("NeteaseDecrypt")
    daemon = MyChromeDaemon()
    # daemon.listen_ready.acquire()  # 等待 ichrome的监听线程开始运行  阻塞
    # daemon.browser.get("https://music.163.com/")

    # handler = Netease_music("E:/workspace/netease-cached-music/cache/", "E:/workspace/netease-cached-music/dst/")
    # handler = Netease_music("C:\\Users\\DogEgg\\AppData\\Local\\Netease\\CloudMusic\\Cache\\Cache",
    #                         "E:/workspace/netease-cached-music/dst/")
    
    # 子线程监视文件夹变动
    handler = Netease_music(srcDir, desDir)
    ob_thread = handler.start_dir_watch()
    
    # 主线程等待 ctrl+c 信号退出
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        a = ob_thread.stop()
        logging.info('key board interrupt.. exit..')
    ob_thread.join()


    # handler.getMusic()
    # print(handler.getInfoFromWeb("65528"))