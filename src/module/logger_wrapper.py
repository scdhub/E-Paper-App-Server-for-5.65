"""ログ出力管理クラス定義
"""
from datetime import datetime
from logging import getLogger, Logger
from os.path import abspath

import logging
import inspect
import sys

class cLoggerWrapper:
    """ログ出力管理クラス
    """

    def __init__(self, LEVEL:int = logging.INFO) -> None:
        """ログ出力管理クラスのコンストラクタ

        Args:
            LEVEL (int, optional): ログ出力レベル. Defaults to logging.INFO.
        """
        self._logger:Logger = getLogger(__name__)
        self._logger.setLevel(LEVEL)
        self._level:int = LEVEL

    def output(self, MSG:str, PREFIX:str = '', LEVEL:int = logging.DEBUG) -> bool:
        """ログの出力
        出力形式:
        現在時刻 ファイルパス(行番号) 【関数名PREFIX】 MSG

        Args:
            MSG (str): 出力内容
            PREFIX (str, optional): 接頭辞. Defaults to ''.
            LEVEL (int, optional): ログ出力レベル. Defaults to logging.DEBUG.

        Returns:
            bool: 成功時はTrue、それ以外はFalse
        """
        ret_value:bool = True
        try:
            NOW:str = datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
            FRAME = inspect.stack()[1]
            FILE_PATH:str = abspath(FRAME.filename)
            LINE_NO:int = FRAME.lineno
            FUNC_NAME:str = FRAME.function
            DST_MSG:str = f'{NOW}\t{FILE_PATH}({LINE_NO})\t【{FUNC_NAME}{PREFIX}】\t{MSG}' if LEVEL >= self._level else ''
            if len(DST_MSG) > 0:
                if LEVEL >= logging.CRITICAL:
                    self._logger.critical(DST_MSG)
                elif LEVEL >= logging.ERROR:
                    self._logger.error(DST_MSG)
                elif LEVEL >= logging.WARN:
                    self._logger.warn(DST_MSG)
                elif LEVEL >= logging.INFO:
                    self._logger.info(DST_MSG)
                else:
                    self._logger.debug(DST_MSG)
        except Exception as e:
            ret_value = False
            print(f'MSG:{MSG}, PREFIX:{PREFIX}, LEVEL:{LEVEL}, {type(e).__name__}! {e}')
        return ret_value
