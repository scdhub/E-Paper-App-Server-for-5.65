"""環境変数管理
"""
import os
from dotenv import load_dotenv

class cEnvMng:
    """環境変数管理クラス
    """

    def __init__(self) -> None:
        """環境変数管理クラスのコンストラクタ
        """
        # 環境変数ファイル読み込み
        load_dotenv(override=True)

    def __str__(self) -> str:
        """現在のオブジェクトを表す文字列を返す

        Returns:
            str: 現在のオブジェクトを表す文字列
        """
        ret_value = ''
        try:
            ret_value += f'AWS_REGION:{self.AWS_REGION}'
            ret_value += f', AWS_S3_BUCKET:{self.AWS_S3_BUCKET}'

            ret_value += f', LOG_LEVEL:{self.LOG_LEVEL}'
        except Exception as e:
            print(f'{type(e).__name__}! {e}')
        return ret_value

    @property
    def AWS_REGION(self) -> str:
        """AWSリージョン名 取得

        Returns:
            str: AWSリージョン名
        """
        return os.getenv('AWS_REGION', '')

    @property
    def AWS_S3_BUCKET(self) -> str:
        """AWS S3バケット名 取得

        Returns:
            str: AWS S3バケット名
        """
        return os.getenv('AWS_S3_BUCKET', '')

    @property
    def LOG_LEVEL(self) -> int:
        """ログ出力レベル 取得

        Returns:
            int: ログ出力レベル
        """
        SRC_VALUE = os.getenv('LOG_LEVEL', '0')
        dst_value = 0
        try:
            dst_value = 0 if not SRC_VALUE.isdigit() else int(SRC_VALUE)
        except Exception as e:
            print(f'{type(e).__name__}! {e}')
        return dst_value
