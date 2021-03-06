# _*_ coding: utf-8 _*_

"""
concur_insts.py by xianhu
"""

import time
import logging
from .abc_base import TPEnum, BaseThread


# ===============================================================================================================================
def work_fetch(self):
    """
    procedure of fetching, auto running, and only return True
    """
    # ----1
    priority, url, keys, deep, repeat = self.pool.get_a_task(TPEnum.URL_FETCH)

    # ----2
    try:
        code, content = self.worker.working(url, keys, repeat)
    except Exception as excep:
        code, content = -1, None
        logging.error("%s.worker.working() error: %s", self.__class__.__name__, excep)

    # ----3
    if code > 0:
        self.pool.update_number_dict(TPEnum.URL_FETCH, +1)
        self.pool.add_a_task(TPEnum.HTM_PARSE, (priority, url, keys, deep, content))
    elif code == 0:
        self.pool.add_a_task(TPEnum.URL_FETCH, (priority+1, url, keys, deep, repeat+1))
    else:
        pass

    # ----4
    self.pool.finish_a_task(TPEnum.URL_FETCH)
    return True

FetchThread = type("FetchThread", (BaseThread,), dict(work=work_fetch))


# ===============================================================================================================================
def work_parse(self):
    """
    procedure of parsing, auto running, and only return True
    """
    # ----1
    priority, url, keys, deep, content = self.pool.get_a_task(TPEnum.HTM_PARSE)

    # ----2
    try:
        code, url_list, save_list = self.worker.working(priority, url, keys, deep, content)
    except Exception as excep:
        code, url_list, save_list = -1, [], []
        logging.error("%s.worker.working() error: %s", self.__class__.__name__, excep)

    # ----3
    if code > 0:
        self.pool.update_number_dict(TPEnum.HTM_PARSE, +1)
        for _url, _keys, _priority in url_list:
            self.pool.add_a_task(TPEnum.URL_FETCH, (_priority, _url, _keys, deep+1, 0))
        for item in save_list:
            self.pool.add_a_task(TPEnum.ITEM_SAVE, (url, keys, item))

    # ----4
    self.pool.finish_a_task(TPEnum.HTM_PARSE)
    return True

ParseThread = type("ParseThread", (BaseThread,), dict(work=work_parse))


# ===============================================================================================================================
def work_save(self):
    """
    procedure of saving, auto running, and only return True
    """
    # ----1
    url, keys, item = self.pool.get_a_task(TPEnum.ITEM_SAVE)

    # ----2
    try:
        result = self.worker.working(url, keys, item)
    except Exception as excep:
        result = False
        logging.error("%s.worker.working() error: %s", self.__class__.__name__, excep)

    # ----3
    if result:
        self.pool.update_number_dict(TPEnum.ITEM_SAVE, +1)

    # ----4
    self.pool.finish_a_task(TPEnum.ITEM_SAVE)
    return True

SaveThread = type("SaveThread", (BaseThread,), dict(work=work_save))


# ===============================================================================================================================
def init_monitor_thread(self, name, pool, sleep_time=5):
    """
    constructor of MonitorThread
    """
    BaseThread.__init__(self, name, None, pool)

    self.sleep_time = sleep_time    # sleeping time in every loop
    self.init_time = time.time()    # initial time of this spider

    self.last_fetch_num = 0         # fetch number in last time
    self.last_parse_num = 0         # parse number in last time
    self.last_save_num = 0          # save number in last time
    return


def work_monitor(self):
    """
    monitor the pool, auto running and return True to continue, False to stop
    """
    time.sleep(self.sleep_time)

    cur_fetch_num = self.pool.number_dict[TPEnum.URL_FETCH]
    cur_parse_num = self.pool.number_dict[TPEnum.HTM_PARSE]
    cur_save_num = self.pool.number_dict[TPEnum.ITEM_SAVE]

    info = "%s status: running_tasks=%s;" % (self.pool.__class__.__name__, self.pool.number_dict[TPEnum.TASKS_RUNNING])

    info += " fetch=(%d, %d, %d/(%ds));" % \
            (self.pool.number_dict[TPEnum.URL_NOT_FETCH], cur_fetch_num, cur_fetch_num-self.last_fetch_num, self.sleep_time)
    self.last_fetch_num = cur_fetch_num

    info += " parse=(%d, %d, %d/(%ds));" % \
            (self.pool.number_dict[TPEnum.HTM_NOT_PARSE], cur_parse_num, cur_parse_num-self.last_parse_num, self.sleep_time)
    self.last_parse_num = cur_parse_num

    info += " save=(%d, %d, %d/(%ds));" % \
            (self.pool.number_dict[TPEnum.ITEM_NOT_SAVE], cur_save_num, cur_save_num-self.last_save_num, self.sleep_time)
    self.last_save_num = cur_save_num

    info += " total_seconds=%d" % (time.time() - self.init_time)

    logging.warning(info)
    return False if self.pool.monitor_stop else True

MonitorThread = type("MonitorThread", (BaseThread,), dict(__init__=init_monitor_thread, work=work_monitor))
