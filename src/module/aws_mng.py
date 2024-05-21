"""AWSアクセス関連処理
"""

import boto3
import boto3.s3
import boto3.s3.constants
import boto3.s3.transfer
import boto3.session
from datetime import datetime
import json
import logging
import os.path as path

from botocore.client import Config
from botocore.exceptions import ClientError
from http import HTTPStatus
from module.common_func import *
from module.logger_wrapper import cLoggerWrapper
from uuid import uuid4

class cAwsAccessMng:
    """AWSアクセス処理クラス
    """

    def __init__(self, REGION_NAME:str = '', S3_BUCKET:str = '', LOGGER_WRAPPER:cLoggerWrapper = None) -> None:
        """AWSアクセス処理クラスのコンストラクタ

        Args:
            REGION_NAME (str, optional): AWSリージョン名. Defaults to ''.
            S3_BUCKET (str, optional): AWS S3バケット名. Defaults to ''.
            LOGGER_WRAPPER (cLoggerWrapper, optional): ログ出力管理クラスのインスタンス. Defaults to None.
        """
        self._region_name = REGION_NAME
        self._s3_bucket_name = S3_BUCKET
        self._s3_client = None
        self._dynamodb_resource = None
        self._logger_wrapper = LOGGER_WRAPPER
        self._image_url_hash_tables:list[dict[str, str|int]] = None

    def __str__(self) -> str:
        """現在のオブジェクトを表す文字列を返す

        Returns:
            str: 現在のオブジェクトを表す文字列
        """
        ret_value = ''
        try:
            ret_value += f'REGION_NAME:{self.REGION_NAME}'
            ret_value += f', S3_BUCKET_NAME:{self.S3_BUCKET_NAME}'
            ret_value += f', len(ImageUrlHashTable):{-1 if self.ImageUrlHashTables is None else len(self.ImageUrlHashTables)}'
        except Exception as e:
            self.LOGGER_WRAPPER.output(MSG=f'ret_value:{ret_value}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value

    @property
    def MAX_S3_FILE_PATH_LENGTH(self) -> int:
        """S3ファイルパスの最大長 取得

        Returns:
            int: S3ファイルパスの最大長
        """
        return 1024

    @property
    def REGION_NAME(self) -> str:
        """AWSリージョン名 取得

        Returns:
            str: AWSリージョン名
        """
        return self._region_name

    @property
    def S3_BUCKET_NAME(self) -> str:
        """AWS S3バケット名 取得

        Returns:
            str: AWS S3バケット名
        """
        return self._s3_bucket_name

    @property
    def S3_PREFIX(self) -> str:
        """AWS S3プレフィックス名 取得

        Returns:
            str: AWS S3プレフィックス名
        """
        return 'images'

    @property
    def S3_CLIENT(self):
        """AWS S3クライアントのインスタンス 取得

        Returns:
            _type_: AWS S3クライアントのインスタンス
        """
        if self._s3_client is None:
            try:
                self._s3_client = boto3.client('s3', config=Config(signature_version='s3v4'), region_name=self.REGION_NAME)
            except Exception as e:
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return self._s3_client

    @property
    def S3_DB_NAME(self) -> str:
        """AWS S3に保持する画像ID・画像変換状態・画像URLのhash-tableリスト管理DB名 取得

        Returns:
            str: AWS S3に保持する画像ID・画像変換状態・画像URLのhash-tableリスト管理DB名
        """
        return 'hash-table.db'

    @property
    def ImageUrlHashTables(self) -> list[dict[str, str|int]]:
        """画像ID・画像変換状態・画像URLのhash-tableリスト 取得

        Returns:
            list[dict[str, str|int]]: 画像ID・画像変換状態・画像URLのhash-tableリスト(ex:[{'id':'abcd...', 'convertible':0, 'url':'http://～'}, ...])
        """
        if self._image_url_hash_tables is None:
            self._image_url_hash_tables = []
        return self._image_url_hash_tables
    @ImageUrlHashTables.setter
    def ImageUrlHashTables(self, value:list[dict[str, str|int]]):
        """画像ID・画像変換状態・画像URLのhash-tableリスト 設定

        Args:
            value (list[dict[str, str|int]]): 画像IDとURLのhash-tableリスト(ex:[{'id':'abcd...', 'convertible':0, 'url':'http://～'}, ...])
        """
        self._image_url_hash_tables = value

    @property
    def LOGGER_WRAPPER(self) -> cLoggerWrapper:
        """ログ出力管理クラスのインスタンス 取得

        Returns:
            cLoggerWrapper: ログ出力管理クラスのインスタンス
        """
        if self._logger_wrapper is None:
            self._logger_wrapper = cLoggerWrapper()
        return self._logger_wrapper

    def initialize(self) -> bool:
        """初期化処理

        Returns:
            bool: 成功時はTrue、それ以外はFalse
        """
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>', PREFIX='::Enter')
        ret_value = not self.S3_CLIENT is None and not cCommonFunc.is_none_or_empty(self.S3_DB_NAME)
        if ret_value:
            try:
                OBJ = self.S3_CLIENT.get_object(Bucket=self.S3_BUCKET_NAME, Key=self.S3_DB_NAME)
                self.ImageUrlHashTables = json.loads(OBJ['Body'].read()) if not OBJ is None and isinstance(OBJ, dict) and 'Body' in OBJ else {}
            except Exception as e:
                # 404エラー(DB不存在)以外のエラーの場合は処理失敗
                if not isinstance(e, ClientError) or e.response['Error']['Code'] != '404':
                    ret_value = False
                    self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>', PREFIX='::Leave')
        return ret_value

    def get_signed_urls_for_put_object(self, IMAGE_FILE_PATHS:list[str], API_RESULT_DATAS:dict[str, str|list], EXPIRATION:int=3600) -> int:
        """ファイルPUT用署名付きURLリストの取得

        Args:
            IMAGE_FILE_PATHS (list[str]): 画像ファイルパスリスト
            API_RESULT_DATAS (dict[str, str|list]): API応答内容dict ※本dict内の"signed_urls"キー(※cCommonFunc.API_RESP_DICT_KEY_SIGNED_URLS と同値)内に署名付きURLリストが含まれている
            EXPIRATION (int, optional): 有効期限(単位:秒). Defaults to 3600.

        Returns:
            int: httpステータスコード
        """
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, len(IMAGE_FILE_PATHS):{-1 if IMAGE_FILE_PATHS is None else len(IMAGE_FILE_PATHS)}, EXPIRATION:{EXPIRATION}', PREFIX='::Enter')
        SIGNED_URLS:list[dict[str, str]] = API_RESULT_DATAS.get(cCommonFunc.API_RESP_DICT_KEY_SIGNED_URLS, None) #: 署名付きURLリスト(key:元画像ファイルパス, value:署名付きURL)
        ret_value = HTTPStatus.OK if not cCommonFunc.is_none_or_empty(IMAGE_FILE_PATHS) and not SIGNED_URLS is None else HTTPStatus.BAD_REQUEST if cCommonFunc.is_none_or_empty(IMAGE_FILE_PATHS) else HTTPStatus.INTERNAL_SERVER_ERROR
        if ret_value != HTTPStatus.OK:
            # リクエストデータに不正がある旨をAPI処理結果詳細に設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'The input image file path list is empty or there is no URL storage location.\nimage file path list length is {0 if cCommonFunc.is_none_or_empty(IMAGE_FILE_PATHS) else len(IMAGE_FILE_PATHS)}')
        elif not self._create_s3_bucket(S3_CLIENT=self.S3_CLIENT, API_RESULT_DATAS=API_RESULT_DATAS):
            ret_value = HTTPStatus.INTERNAL_SERVER_ERROR

        # 通常は空リストが設定されているはずだが、念のため署名付きURLリストをクリア
        if not SIGNED_URLS is None: SIGNED_URLS.clear()
        if ret_value == HTTPStatus.OK:
            try:
                NOW_TIME:datetime = datetime.now()
                # S3バケット内ディレクトリ名
                DIR_NAME = self._get_adjust_s3_naming_convention(SRC=f'{NOW_TIME.strftime("%Y")}/{NOW_TIME.strftime("%m")}', PREFIX_LENGTH=len(f'{self.S3_PREFIX}/00-00-00-00.000-{len(str(uuid4()))}.jpeg')+1)
                for SRC_FILE_PATH in IMAGE_FILE_PATHS:
                    FILE_EXT = path.splitext(SRC_FILE_PATH.replace('\\', '/'))[1]
                    FILE_NAME = f'{NOW_TIME.strftime("%m-%d-%H-%M-%S.%f")[:-3]}-{str(uuid4())}{FILE_EXT}'
                    # S3バケット内に「images/yyyy/mm/mm-dd-HH-MM-SS.fff-UID.(元ファイル拡張子)」というファイル名での署名付きURLを取得
                    URL = self._get_signed_url(S3_CLIENT=self.S3_CLIENT, CLIENT_METHOD='put_object', EXPIRATION=EXPIRATION, OBJECT_KEY=self._get_adjust_s3_naming_convention(SRC=f'{self.S3_PREFIX}/{DIR_NAME}/{FILE_NAME}'))
                    SIGNED_URLS.append({SRC_FILE_PATH:URL})
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, len(IMAGE_FILE_PATHS):{-1 if IMAGE_FILE_PATHS is None else len(IMAGE_FILE_PATHS)}, EXPIRATION:{EXPIRATION}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, len(IMAGE_FILE_PATHS):{-1 if IMAGE_FILE_PATHS is None else len(IMAGE_FILE_PATHS)}, EXPIRATION:{EXPIRATION}, len(SIGNED_URLS):{-1 if SIGNED_URLS is None else len(SIGNED_URLS)}, ret_value:{ret_value}', PREFIX='::Leave')
        return ret_value

    def update_hash_table(self, API_RESULT_DATAS:dict[str, str]) -> int:
        """画像IDとURLのhash-tableアップデート

        Args:
            API_RESULT_DATAS (dict[str, str]): API応答内容dict

        Returns:
            int: httpステータスコード
        """
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>', PREFIX='::Enter')
        S3_IMAGE_FILE_PATHS:list[str] = []
        # AWS S3内画像ファイルパス一覧取得 →　S3_IMAGE_FILE_PATHSに設定
        ret_value = self._get_s3_file_lists(API_RESULT_DATAS=API_RESULT_DATAS, IMAGE_FILE_PATHS=S3_IMAGE_FILE_PATHS)

        # AWS S3内画像ファイルパス一覧取得成功
        if ret_value == HTTPStatus.OK:
            # hash-tableリストにテーブル追加
            ret_value = self._append_hash_tables_from_s3(API_RESULT_DATAS=API_RESULT_DATAS, S3_IMAGE_FILE_PATHS=S3_IMAGE_FILE_PATHS)

        # テーブル追加成功
        if ret_value == HTTPStatus.OK:
            # DB更新
            ret_value = self._update_hash_table_db(API_RESULT_DATAS=API_RESULT_DATAS)

        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, len(S3_IMAGE_FILE_PATHS):{len(S3_IMAGE_FILE_PATHS)}, ret_value:{ret_value}', PREFIX='::Leave')
        return ret_value

    def get_images(self, COUNT:int, API_RESULT_DATAS:dict[str, str|list], EXPIRATION:int=3600) -> int:
        """画像リスト取得

        Args:
            COUNT (int): 取得する画像リスト数(0の場合は全件取得)
            API_RESULT_DATAS (dict[str, str | list]): API応答内容dict ※本dict内の"data"キー(※cCommonFunc.API_RESP_DICT_KEY_DATA と同値)内に画像IDと画像URLリストが設定される
            EXPIRATION (int, optional): 有効期限(単位:秒). Defaults to 3600.

        Returns:
            int: httpステータスコード
        """
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, COUNT:{COUNT}, EXPIRATION:{EXPIRATION}', PREFIX='::Enter')
        DATAS:list[dict[str, str]] = None if API_RESULT_DATAS is None else API_RESULT_DATAS.get(cCommonFunc.API_RESP_DICT_KEY_DATA, None)
        ret_value = HTTPStatus.OK if COUNT >= 0 and not DATAS is None and not self.ImageUrlHashTables is None else HTTPStatus.BAD_REQUEST if COUNT < 0 else HTTPStatus.INTERNAL_SERVER_ERROR
        if ret_value == HTTPStatus.OK:
            try:
                DATAS.clear()
                for TABLE in self.ImageUrlHashTables:
                    URL:str = TABLE.get(cCommonFunc.API_RESP_DICT_KEY_URL, '')
                    CONVERTIBLE:eImageConvertibleKind = TABLE.get(cCommonFunc.API_RESP_DICT_KEY_CONVERTIBLE, eImageConvertibleKind.UNDETERMINED)
                    DATAS.append({cCommonFunc.API_RESP_DICT_KEY_ID:TABLE.get(cCommonFunc.API_RESP_DICT_KEY_ID, ''), cCommonFunc.API_RESP_DICT_KEY_URL:self._get_signed_url(S3_CLIENT=self.S3_CLIENT, CLIENT_METHOD='get_object', EXPIRATION=EXPIRATION, OBJECT_KEY=URL), cCommonFunc.API_RESP_DICT_KEY_CONVERTIBLE:eImageConvertibleKind.get_name_from_value(VALUE=CONVERTIBLE)})
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, COUNT:{COUNT}, EXPIRATION:{EXPIRATION}, len(DATAS):{-1 if DATAS is None else len(DATAS)}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        elif ret_value == HTTPStatus.BAD_REQUEST:
            # リクエストデータに不正がある旨をAPI処理結果詳細に設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'COUNT is less than 0!\n\tCOUNT:{COUNT}')
        else:
            # 内部変数に不正がある旨をAPI処理結果詳細に設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'hash-tables is None or internal parameter is invalid!\n\tlen(DATAS):{-1 if DATAS is None else len(DATAS)}')
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, COUNT:{COUNT}, EXPIRATION:{EXPIRATION}, len(DATAS):{-1 if DATAS is None else len(DATAS)}, ret_value:{ret_value}', PREFIX='::Leave')
        return ret_value

    def get_signed_urls_for_get_object_to_id(self, ID:str, API_RESULT_DATAS:dict[str, str], EXPIRATION:int=3600) -> int:
        """IDに該当する署名付きURL(画像ダウンロード用)を取得する

        Args:
            ID (str): 画像ID
            API_RESULT_DATAS (dict[str, str]): API応答内容dict
            EXPIRATION (int, optional): 有効期限(単位:秒). Defaults to 3600.

        Returns:
            int: httpステータスコード
        """
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, ID:{ID}, EXPIRATION:{EXPIRATION}', PREFIX='::Enter')
        # IDがhash-table内に存在するか
        ret_value = HTTPStatus.OK if self._is_exist_value_in_hash_table(KEY=cCommonFunc.API_RESP_DICT_KEY_ID, DST_VALUE=ID) else HTTPStatus.BAD_REQUEST
        if ret_value == HTTPStatus.OK:
            SRC_URL = [HASH_TABLE for HASH_TABLE in self.ImageUrlHashTables if HASH_TABLE.get(cCommonFunc.API_RESP_DICT_KEY_ID, '') == ID][0].get(cCommonFunc.API_RESP_DICT_KEY_URL, '')
            # 署名付きURL(画像ダウンロード用)をAPI応答内容dictに設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=self._get_signed_url(S3_CLIENT=self.S3_CLIENT, CLIENT_METHOD='get_object', EXPIRATION=EXPIRATION, OBJECT_KEY=SRC_URL), KEY=cCommonFunc.API_RESP_DICT_KEY_URL)
        else:
            # リクエストデータに不正がある旨をAPI処理結果詳細に設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'ID is not exist in table!\n\tID:{ID}')
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, ID:{ID}, EXPIRATION:{EXPIRATION}, ret_value:{ret_value}', PREFIX='::Leave')
        return ret_value

    def update_hash_table_image_convertible_state(self, ID:str, CONVERTIBLE:str, API_RESULT_DATAS:dict[str, str]) -> int:
        """画像ID・画像変換状態・画像URLのhash-tableの画像変換状態を更新

        Args:
            ID (str): 画像ID
            CONVERTIBLE (str): 画像変換状態(ex:'UNDETERMINED')
            API_RESULT_DATAS (dict[str, str]): API応答内容dict

        Returns:
            int: httpステータスコード
        """
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, ID:{ID}, CONVERTIBLE:{CONVERTIBLE}', PREFIX='::Enter')
        # IDがhash-table内に存在するか
        ret_value = HTTPStatus.OK if self._is_exist_value_in_hash_table(KEY=cCommonFunc.API_RESP_DICT_KEY_ID, DST_VALUE=ID) else HTTPStatus.BAD_REQUEST
        if ret_value == HTTPStatus.OK:
            DST_TABLE = [HASH_TABLE for HASH_TABLE in self.ImageUrlHashTables if HASH_TABLE.get(cCommonFunc.API_RESP_DICT_KEY_ID, '') == ID][0]
            # hash-tableの画像変換状態を更新
            DST_TABLE[cCommonFunc.API_RESP_DICT_KEY_CONVERTIBLE] = eImageConvertibleKind.get_value_from_name(NAME=CONVERTIBLE)
            # DB更新
            ret_value = self._update_hash_table_db(API_RESULT_DATAS=API_RESULT_DATAS)
        else:
            # リクエストデータに不正がある旨をAPI処理結果詳細に設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'ID is not exist in table!\n\tID:{ID}')
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, ID:{ID}, CONVERTIBLE:{CONVERTIBLE}, ret_value:{ret_value}', PREFIX='::Leave')
        return ret_value

    def _create_s3_bucket(self, S3_CLIENT, API_RESULT_DATAS:dict[str, str]) -> bool:
        """S3バケットの作成

        Args:
            S3_CLIENT (_type_): S3クライアントのインスタンス
            API_RESULT_DATAS (dict[str, str]): API応答内容dict

        Returns:
            bool: 成功時(バケットが既に存在する場合含)はTrue、それ以外はFalse
        """
        ret_value = not S3_CLIENT is None
        # バケット不存在
        if ret_value and not self._is_exist_s3_bucket(S3_CLIENT=S3_CLIENT, API_RESULT_DATAS=API_RESULT_DATAS):
            try:
                S3_CLIENT.create_bucket(Bucket=self.S3_BUCKET_NAME,CreateBucketConfiguration={'LocationConstraint': self.REGION_NAME}, ObjectOwnership='ObjectWriter')
                S3_CLIENT.put_public_access_block(Bucket=self.S3_BUCKET_NAME, PublicAccessBlockConfiguration={'BlockPublicAcls': False,'IgnorePublicAcls': False,'BlockPublicPolicy': False,'RestrictPublicBuckets': False})
                S3_CLIENT.put_bucket_acl(ACL='public-read',Bucket=self.S3_BUCKET_NAME)
                S3_CLIENT.put_bucket_policy(Bucket=self.S3_BUCKET_NAME, Policy=f'{{"Version": "2012-10-17", "Statement": [{{ "Sid": "public","Effect": "Allow","Principal": "*", "Action": ["s3:GetObject"], "Resource": ["arn:aws:s3:::{self.S3_BUCKET_NAME}/*"] }} ]}}')
            except Exception as e:
                ret_value = False
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value

    def _is_exist_s3_bucket(self, S3_CLIENT, API_RESULT_DATAS:dict[str, str]) -> bool:
        """S3バケットの存在チェック

        Args:
            S3_CLIENT (_type_): S3クライアントのインスタンス
            API_RESULT_DATAS (dict[str, str]): API応答内容dict

        Returns:
            bool: S3バケットが存在する場合はTrue、それ以外はFalse
        """
        ret_value = not S3_CLIENT is None
        if ret_value:
            try:
                S3_CLIENT.head_bucket(Bucket=self.S3_BUCKET_NAME)
            except ClientError as e:
                ret_value = False
                # 404エラー(バケット不存在)以外のエラーの場合はAPI処理結果詳細にメッセージを設定する
                if e.response['Error']['Code'] != '404':
                    cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                    self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
            except Exception as e:
                ret_value = False
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value

    def _get_adjust_s3_naming_convention(self, SRC:str, PREFIX_LENGTH:int = 0) -> str:
        """S3命名規則に沿ったフォルダ/ファイル名の取得
        []
        ・大文字、小文字、数字、ピリオド(.)、アンスコ(_)、ダッシュ(-)、を含めることができます。
        クエスチョン(?)、アンド(&)、ドル($)、シャープ(#)、パーセント(%)、ダブルクオート(")、シングルクオート(')、を含めることができますが、エスケープ文字とする必要があります。
        スラッシュ(/)を使うことはできない。
        1文字以上

        Args:
            SRC (str): 元フォルダ/ファイル名
            PREFIX_LENGTH (int, optional): (フォルダ名チェックの場合に指定)ファイル名の最大長. Defaults to 0.

        Returns:
            str: S3命名規則に沿ったフォルダ/ファイル名
        """
        ret_value:str = SRC
        if not cCommonFunc.is_none_or_empty(SRC):
            try:
                # 「フォルダ+ファイルパス」で1024文字以内に収める
                ret_value = ret_value[:self.MAX_S3_FILE_PATH_LENGTH]
            except Exception as e:
                self.LOGGER_WRAPPER.output(MSG=f'SRC:{SRC}, PREFIX_LENGTH:{PREFIX_LENGTH}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value

    def _get_signed_url(self, S3_CLIENT, CLIENT_METHOD:str, EXPIRATION:int, OBJECT_KEY:str) -> str:
        """署名付きURLの取得

        Args:
            S3_CLIENT (_type_): S3クライアントのインスタンス
            CLIENT_METHOD (str): S3へのリクエストで利用するAPI(ex:"put_object", "get_object")
            EXPIRATION (int): 有効期限(単位:秒)
            OBJECT_KEY (str): ファイル名

        Returns:
            str: 署名付きURL
        """
        url:str = ''
        if not S3_CLIENT is None and not cCommonFunc.is_none_or_empty(OBJECT_KEY):
            try:
                url = S3_CLIENT.generate_presigned_url(ClientMethod=CLIENT_METHOD, Params={'Bucket': self.S3_BUCKET_NAME, 'Key': f'{OBJECT_KEY}'}, ExpiresIn=EXPIRATION)
            except Exception as e:
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, CLIENT_METHOD:{CLIENT_METHOD}, EXPIRATION:{EXPIRATION}, OBJECT_KEY:{OBJECT_KEY}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return url

    def _get_s3_file_lists(self, API_RESULT_DATAS:dict[str, str], IMAGE_FILE_PATHS:list[dict]) -> int:
        """AWS S3内ファイルパス一覧を取得

        Args:
            API_RESULT_DATAS (dict[str, str]): API応答内容dict
            IMAGE_FILE_PATHS (list[dict]): AWS S3内ファイルパス一覧

        Returns:
            int: httpステータスコード
        """
        self.LOGGER_WRAPPER.output(MSG=f'', PREFIX='::Enter')
        ret_value = HTTPStatus.OK if not IMAGE_FILE_PATHS is None else HTTPStatus.INTERNAL_SERVER_ERROR
        # バケットが存在する場合
        if ret_value == HTTPStatus.OK and self._is_exist_s3_bucket(S3_CLIENT=self.S3_CLIENT, API_RESULT_DATAS=API_RESULT_DATAS):
            try:
                IMAGE_FILE_PATHS.clear()
                # S3内のファイル一覧を取得
                OBJECTS = self.S3_CLIENT.list_objects(Bucket=self.S3_BUCKET_NAME, Prefix=self.S3_PREFIX)
                self.LOGGER_WRAPPER.output(MSG=f'OBJECTS:{OBJECTS}', PREFIX='::Debug1') # TODO:後で消す
                if 'CommonPrefixes' in OBJECTS:
                    IMAGE_FILE_PATHS.extend([content['Prefix'] for content in OBJECTS['CommonPrefixes']])
                if 'Contents' in OBJECTS:
                    for content in OBJECTS['Contents']:
                        if 'Key' in content and content['Size'] > 0:
                            IMAGE_FILE_PATHS.append(content['Key'])
                self.LOGGER_WRAPPER.output(MSG=f'IMAGE_FILE_PATHS:{IMAGE_FILE_PATHS}', PREFIX='::Debug2') # TODO:後で消す
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'len(IMAGE_FILE_PATHS):{len(IMAGE_FILE_PATHS)}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        self.LOGGER_WRAPPER.output(MSG=f'len(IMAGE_FILE_PATHS):{len(IMAGE_FILE_PATHS)}, ret_value:{ret_value}', PREFIX='::Leave')
        return ret_value

    def _append_hash_tables_from_s3(self, API_RESULT_DATAS:dict[str, str], S3_IMAGE_FILE_PATHS:list[str]) -> int:
        """画像ID・画像変換状態・画像URLのhash-tableリストにS3画像ファイルパスからテーブルを追加

        Args:
            API_RESULT_DATAS (dict[str, str]): API応答内容dict
            S3_IMAGE_FILE_PATHS (list[str]): AWS S3内画像ファイルパスリスト

        Returns:
            int: httpステータスコード
        """
        ret_value = HTTPStatus.OK if not self.ImageUrlHashTables is None and not S3_IMAGE_FILE_PATHS is None else HTTPStatus.INTERNAL_SERVER_ERROR

        # 引数正常
        if ret_value == HTTPStatus.OK:
            try:
                for FILE_PATH in S3_IMAGE_FILE_PATHS:
                    # hash-tableに存在しない画像ファイルパスの場合
                    if not self._is_exist_value_in_hash_table(KEY=cCommonFunc.API_RESP_DICT_KEY_URL, DST_VALUE=FILE_PATH):
                        TABLE:dict[str, str] = {}
                        FILE_BASE_NAME:str = path.basename(FILE_PATH)
                        # ID:ファイル名(※署名付きURL取得時にuuid4によるユニークIDが付与されており、S3アップロード時にユニークIDは既に存在する)
                        TABLE[cCommonFunc.API_RESP_DICT_KEY_ID] = path.splitext(FILE_BASE_NAME)[0]
                        TABLE[cCommonFunc.API_RESP_DICT_KEY_URL] = FILE_PATH
                        TABLE[cCommonFunc.API_RESP_DICT_KEY_CONVERTIBLE] = eImageConvertibleKind.UNDETERMINED
                        self.ImageUrlHashTables.append(TABLE)
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, len(API_RESULT_DATAS):{-1 if API_RESULT_DATAS is None else len(API_RESULT_DATAS)}, len(S3_IMAGE_FILE_PATHS):{-1 if S3_IMAGE_FILE_PATHS is None else len(S3_IMAGE_FILE_PATHS)}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        else:
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'hash-tables is None or parameter is invalid!\n, len(S3_IMAGE_FILE_PATHS):{-1 if S3_IMAGE_FILE_PATHS is None else len(S3_IMAGE_FILE_PATHS)}')

        return ret_value

    def _update_hash_table_db(self, API_RESULT_DATAS:dict[str, str]) -> int:
        """hash-table DB更新(※DBが存在しない場合は新規作成)

        Args:
            API_RESULT_DATAS (dict[str, str]): API応答内容dict

        Returns:
            int: httpステータスコード
        """
        ret_value = HTTPStatus.OK if not self.ImageUrlHashTables is None and not cCommonFunc.is_none_or_empty(self.S3_BUCKET_NAME) and not cCommonFunc.is_none_or_empty(self.S3_DB_NAME) else HTTPStatus.INTERNAL_SERVER_ERROR
        if ret_value == HTTPStatus.OK:
            try:
                # DB更新
                self.S3_CLIENT.put_object(Body=json.dumps(self.ImageUrlHashTables), Bucket=self.S3_BUCKET_NAME, Key=self.S3_DB_NAME)
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        else:
            # 内部変数に不正がある旨をAPI処理結果詳細に設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'hash-tables is None or internal parameter is invalid!, len(self.S3_BUCKET_NAME):{len(self.S3_BUCKET_NAME)}, len(self.S3_DB_NAME):{len(self.S3_DB_NAME)}')
        return ret_value

    def _is_exist_value_in_hash_table(self, KEY:str, DST_VALUE:str) -> bool:
        """hash-tableの該当keyに値が存在するかチェック

        Args:
            KEY (str): hash-tableキー名
            DST_VALUE (str): 検索対象値

        Returns:
            bool: hash-tableの該当keyに値が存在する場合はTrue、それ以外はFalse
        """
        ret_value = not self.ImageUrlHashTables is None
        if ret_value:
            try:
                ret_value = any(DST_VALUE == HASH_TABLE.get(KEY, '') for HASH_TABLE in self.ImageUrlHashTables)
            except Exception as e:
                ret_value = False
                self.LOGGER_WRAPPER.output(MSG=f'KEY:{KEY}, DST_VALUE:{DST_VALUE}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value
