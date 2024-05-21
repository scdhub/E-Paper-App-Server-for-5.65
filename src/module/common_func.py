"""共通処理
"""

from enum import IntEnum, auto

class eImageConvertibleKind(IntEnum):
    """画像フォーマット変換状態を表す列挙型
    """
    UNDETERMINED = auto()
    """未判定
    """
    ENABLED = auto()
    """変換可能
    """
    INVALID = auto()
    """変換不可
    """

    @classmethod
    def get_name_from_value(cls, VALUE:int) -> str:
        """列挙型の値に合致する名称を取得する

        Args:
            VALUE (int): 列挙型の値

        Returns:
            str: 列挙型の値に合致する名称
        """
        ret_value = cls.UNDETERMINED.name.lower()
        for CLS_VAL in cls:
            if VALUE == CLS_VAL:
                ret_value = CLS_VAL.name.lower()
                break
        return ret_value

    @classmethod
    def get_value_from_name(cls, NAME:str) -> IntEnum:
        """名称に合致する列挙型の値を取得する

        Args:
            NAME (str): 名称

        Returns:
            IntEnum: 名称に合致する列挙型の値
        """
        ret_value = cls.UNDETERMINED
        if not cCommonFunc.is_none_or_empty(NAME):
            DST_NAME = NAME.lower()
            for VALUE in cls:
                if DST_NAME == VALUE.name.lower():
                    ret_value = VALUE
                    break
        return ret_value

class cCommonFunc():
    """共通処理定義クラス
    """

    API_RESP_DICT_KEY_RESULT:str = 'result'
    """API応答内容の"処理結果"キー名
    """

    API_RESP_DICT_KEY_RESULT_DETAIL:str = 'result_detail'
    """API応答内容の"処理結果詳細"キー名
    """

    API_RESP_DICT_KEY_SIGNED_URLS:str = 'signed_urls'
    """API応答内容の"署名付きURL"キー名
    """

    API_RESP_DICT_KEY_DATA = 'data'
    """API応答内容の"データ"キー名
    """

    API_RESP_DICT_KEY_ID = 'id'
    """API応答内容の"id"キー名
    """

    API_RESP_DICT_KEY_CONVERTIBLE = 'convertible'
    """API応答内容の"画像フォーマット変換状態"キー名
    """

    API_RESP_DICT_KEY_URL = 'url'
    """API応答内容の"URL"キー名
    """

    @classmethod
    def is_none_or_empty(cls, SRC:str | list | dict) -> bool:
        """Noneか空かチェック

        Args:
            SRC (str | list | dict): チェック対象変数

        Returns:
            bool: Noneか空の場合はTrue、それ以外はFalse
        """
        return SRC is None or len(SRC) <= 0

    @classmethod
    def set_api_resp_str_msg(cls, API_RESULT_DATAS:dict[str, str], VALUE:str, KEY:str=API_RESP_DICT_KEY_RESULT_DETAIL) -> bool:
        """キーに該当するAPI応答内容dictのvalue(str型)を設定

        Args:
            API_RESULT_DATAS (dict[str, str]): API応答内容dict
            VALUE (str): 設定内容
            KEY (str, optional): API応答内容dictのキー. Defaults to API_RESP_DICT_KEY_RESULT_DETAIL.

        Returns:
            bool: 成功時はTrue、それ以外はFalse
        """
        ret_value = not API_RESULT_DATAS is None and isinstance(API_RESULT_DATAS, dict)
        if ret_value:
            API_RESULT_DATAS[KEY] = VALUE
        return ret_value
