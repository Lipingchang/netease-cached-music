from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, LoggingEventHandler
from configparser import ConfigParser
import logging,os,re
import sqlite3

class MyDB:
    def __init__(self, db_path, check_same_thread=True):
        # self.db_filename = db_filename
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.check_same_thread = check_same_thread
        self.init_db()

    def __del__(self):
        if self.conn is not None:
            self.conn.close()
            logging.info(f'db {self.db_path} close')

    def init_db(self):
        logging.info(f"sqlite db: {self.db_path}")
        conn = sqlite3.connect(self.db_path,check_same_thread=self.check_same_thread) # 装载 or 新建

        cursor = conn.cursor()
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS "CACHE_FILE_T" (
                id INTEGER PRIMARY KEY autoincrement,         -- '主键',
                song_id TEXT,                -- '网页上的歌曲id',
                song_rate INTEGER,              -- '缓存文件名中的码率',
                file_size INTEGER,              -- 文件大小
                file_createtime INTEGER,        -- 文件创建时间,
                file_modifytime INTEGER,        -- 文件修改时间,
                file_filename TEXT,              -- '缓存文件名',
                title TEXT, -- '歌曲名',
                album TEXT, -- '专辑',
                artist TEXT, -- '艺术家',
                imgUrl TEXT, -- '封面url',
                lyrics TEXT -- '歌词'
            )
        ''')
        # 提交事务
        conn.commit()
        self.conn = conn
        self.cursor = cursor
        logging.info(f'db {self.db_path} init done..')
        return conn

def load_cache_file_info(f_path):
    f_size = os.path.getsize(f_path)  # 获取文件大小，单位为字节
    f_mtime = os.path.getmtime(f_path)  # 获取文件修改日期
    f_ctime = os.path.getctime(f_path)  # 获取文件创建日期
    fname = os.path.basename(f_path)
    [song_id,song_rate, __] = fname.split('-')

    return [f_size,f_mtime,f_ctime,song_id,song_rate]

# 获取缓存文件uc列表
def load_cache_file_info_list(src_dir):
    uc_files = [f for f in os.listdir(src_dir) if f.endswith('.uc')]
    f_info_list = []
    for fname in uc_files:
        f_path = os.path.join(src_dir, fname)
        [f_size,f_mtime,f_ctime,song_id, song_rate] = load_cache_file_info(f_path)

        f_info_list.append({
            "s_id": song_id,
            "s_r": song_rate,
            "f_s": f_size//1024,
            "f_mt": f_mtime,
            "f_ct": f_ctime,
            "f_nm": fname,
        })
    return f_info_list;

# 获取已经转码的文件列表
def load_ready_music_file_info_list(dst_dir):
    ready_msc_dir = os.path.join(dst_dir,'readyMusic')  # 处理完毕的音乐文件
    msc_files = [f for f in os.listdir(ready_msc_dir) ]
    song_id_list = []
    for f in msc_files:
        rst = re.match(r'.* - (\d*)\..*', f)
        if rst is None:
            continue
        song_id_list.append(rst.group(1))
    return song_id_list

# 找到已缓存 但是没有转码的文件
def filter_not_decrypt_file(src_dir, dst_dir):
    cache_info_list =load_cache_file_info_list(src_dir)
    msc_id_list = load_ready_music_file_info_list(dst_dir)
    return list(filter(lambda x:str(x["s_id"]) not in [str(x) for x in msc_id_list],  cache_info_list))




if __name__ == '__main__':
    config = ConfigParser()
    config.read('./decrypt.config')
    srcDir = config["global"]["srcDir"]
    desDir = config["global"]["desDir"]
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%H:%M:%S')
    logging = logging.getLogger("NeteaseDecrypt_db")

    db_filename = config["global"]["dbFilename"]
    db_path = os.path.join(os.getcwd(), db_filename)

    db = MyDB(db_path)
    # rr = filter_not_decrypt_file(srcDir, desDir)
    # print(rr)

