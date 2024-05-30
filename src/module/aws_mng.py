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

from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer
from botocore.client import Config
from botocore.exceptions import ClientError
from datetime import datetime
from http import HTTPStatus
from module.common_func import *
from module.logger_wrapper import cLoggerWrapper
from uuid import uuid4

class cAwsAccessMng:
    """AWSアクセス処理クラス
    """

    def __init__(self, REGION_NAME:str = '', S3_BUCKET:str = '', DYNAMO_DB_IMAGE_MNG_TABLE_NAME:str = '', LOGGER_WRAPPER:cLoggerWrapper = None) -> None:
        """AWSアクセス処理クラスのコンストラクタ

        Args:
            REGION_NAME (str, optional): AWSリージョン名. Defaults to ''.
            S3_BUCKET (str, optional): AWS S3バケット名. Defaults to ''.
            DYNAMO_DB_IMAGE_MNG_TABLE_NAME (str, optional): 画像IDとURL管理DynamoDBテーブル名. Defaults to ''.
            LOGGER_WRAPPER (cLoggerWrapper, optional): ログ出力管理クラスのインスタンス. Defaults to None.
        """
        self._region_name = REGION_NAME
        self._s3_bucket_name = S3_BUCKET
        self._db_image_mng_table_name = DYNAMO_DB_IMAGE_MNG_TABLE_NAME
        self._logger_wrapper = LOGGER_WRAPPER
        self._s3_client = None
        self._dynamodb_client = None
        self._dynamodb_img_mng_resource = None
        self._serializer:TypeSerializer = None
        self._deserializer:TypeDeserializer = None

    def __str__(self) -> str:
        """現在のオブジェクトを表す文字列を返す

        Returns:
            str: 現在のオブジェクトを表す文字列
        """
        ret_value = ''
        try:
            ret_value += f'REGION_NAME:{self.REGION_NAME}'
            ret_value += f', S3_BUCKET_NAME:{self.S3_BUCKET_NAME}'
            ret_value += f', DYNAMO_DB_IMAGE_MNG_TABLE_NAME:{self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME}'
        except Exception as e:
            self.LOGGER_WRAPPER.output(MSG=f'ret_value:{ret_value}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value

    @property
    def Serializer(self) -> TypeSerializer:
        """dict → DynamoDB JSON変換を行うクラスのインスタンス 取得

        Returns:
            TypeSerializer: dict → DynamoDB JSON変換を行うクラスのインスタンス
        """
        if self._serializer is None:
            try:
                self._serializer = TypeSerializer()
            except Exception as e:
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return self._serializer

    @property
    def Deserializer(self) -> TypeDeserializer:
        """DynamoDB JSON → dict変換を行うクラスのインスタンス 取得

        Returns:
            TypeDeserializer: DynamoDB JSON → dict変換を行うクラスのインスタンス
        """
        if self._deserializer is None:
            try:
                self._deserializer = TypeDeserializer()
            except Exception as e:
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return self._deserializer

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
    def DYNAMO_DB_IMAGE_MNG_TABLE_NAME(self) -> str:
        """画像IDとURL管理DynamoDBテーブル名 取得

        Returns:
            str: 画像IDとURL管理DynamoDBテーブル名
        """
        return self._db_image_mng_table_name

    @property
    def DynamoDBClient(self):
        """AWS DynamoDBクライアントのインスタンス 取得

        Returns:
            _type_: AWS DynamoDBクライアントのインスタンス
        """
        if self._dynamodb_client is None:
            try:
                self._dynamodb_client = boto3.client('dynamodb', region_name=self.REGION_NAME)
            except Exception as e:
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return self._dynamodb_client

    @property
    def ImageMngDynamoDbResource(self):
        """AWS DynamoDBリソースのインスタンス 取得

        Returns:
            _type_: AWS DynamoDBリソースのインスタンス
        """
        if self._dynamodb_img_mng_resource is None:
            try:
                self._dynamodb_img_mng_resource = boto3.resource(service_name='dynamodb', region_name=self.REGION_NAME)
            except Exception as e:
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        # テーブル作成
        self._create_dynamo_db_table(DB_RESOURCE=self._dynamodb_img_mng_resource, TABLE_NAME=self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME, ATTRIBUTE_DEFINITIONS=[{'AttributeName':cCommonFunc.API_RESP_DICT_KEY_ID, 'AttributeType':'S'}], KEY_SCHEMA=[{'AttributeName':cCommonFunc.API_RESP_DICT_KEY_ID, 'KeyType':'HASH'}], PROVISIONED_THROUGHPUT={'ReadCapacityUnits':5, 'WriteCapacityUnits':5})
        return self._dynamodb_img_mng_resource

    @property
    def S3_DB_NAME(self) -> str:
        """AWS S3に保持する画像ID・画像変換状態・画像URLのhash-tableリスト管理DB名 取得

        Returns:
            str: AWS S3に保持する画像ID・画像変換状態・画像URLのhash-tableリスト管理DB名
        """
        return 'hash-table.db'

    @property
    def LOGGER_WRAPPER(self) -> cLoggerWrapper:
        """ログ出力管理クラスのインスタンス 取得

        Returns:
            cLoggerWrapper: ログ出力管理クラスのインスタンス
        """
        if self._logger_wrapper is None:
            self._logger_wrapper = cLoggerWrapper()
        return self._logger_wrapper

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

    def force_update_image_mng_hash_table(self, API_RESULT_DATAS:dict[str, str]) -> int:
        """画像IDとURLのhash-table強制アップデート

        Args:
            API_RESULT_DATAS (dict[str, str]): API応答内容dict

        Returns:
            int: httpステータスコード
        """
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>', PREFIX='::Enter')
        S3_IMAGE_FILE_PATHS:list[dict] = []
        # AWS S3内画像ファイルパス一覧取得 →　S3_IMAGE_FILE_PATHSに設定
        ret_value = self._get_s3_file_lists(API_RESULT_DATAS=API_RESULT_DATAS, IMAGE_FILE_PATHS=S3_IMAGE_FILE_PATHS)

        image_hash_table:list[dict[str, str|int]] = None
        # AWS S3内画像ファイルパス一覧取得成功
        if ret_value == HTTPStatus.OK:
            # hash-tableリストにテーブル追加
            ret_value, image_hash_table = self._append_hash_tables_from_s3(API_RESULT_DATAS=API_RESULT_DATAS, S3_IMAGE_FILE_PATH_DICTS=S3_IMAGE_FILE_PATHS)

        # テーブル追加成功
        if ret_value == HTTPStatus.OK:
            # DB更新
            ret_value = self._force_update_db_from_hash_table(API_RESULT_DATAS=API_RESULT_DATAS, IMAGE_HASH_TABLE=image_hash_table)

        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, len(S3_IMAGE_FILE_PATHS):{len(S3_IMAGE_FILE_PATHS)}, len(IMAGE_HASH_TABLE):{-1 if image_hash_table is None else len(image_hash_table)}, ret_value:{ret_value}', PREFIX='::Leave')
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
        IMAGE_HASH_TABLE:list[dict[str, str|int]] = []
        ret_value = HTTPStatus.OK if COUNT >= 0 and not DATAS is None and self._set_image_url_hash_table_from_db(IMAGE_HASH_TABLES=IMAGE_HASH_TABLE) else HTTPStatus.BAD_REQUEST if COUNT < 0 else HTTPStatus.INTERNAL_SERVER_ERROR
        if ret_value == HTTPStatus.OK:
            try:
                DATAS.clear()
                for TABLE in IMAGE_HASH_TABLE:
                    URL:str = TABLE.get(cCommonFunc.API_RESP_DICT_KEY_URL, '')
                    CONVERTIBLE:eImageConvertibleKind = TABLE.get(cCommonFunc.API_RESP_DICT_KEY_CONVERTIBLE, eImageConvertibleKind.UNDETERMINED)
                    DATAS.append({cCommonFunc.API_RESP_DICT_KEY_ID:TABLE.get(cCommonFunc.API_RESP_DICT_KEY_ID, ''), cCommonFunc.API_RESP_DICT_KEY_URL:self._get_signed_url(S3_CLIENT=self.S3_CLIENT, CLIENT_METHOD='get_object', EXPIRATION=EXPIRATION, OBJECT_KEY=URL), cCommonFunc.API_RESP_DICT_KEY_LAST_MODIFIED:TABLE.get(cCommonFunc.API_RESP_DICT_KEY_LAST_MODIFIED, ""), cCommonFunc.API_RESP_DICT_KEY_CONVERTIBLE:eImageConvertibleKind.get_name_from_value(VALUE=CONVERTIBLE)})
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
        ret_value = HTTPStatus.OK if self._is_exist_id_in_dynamodb_image_mng_table(ID=ID) else HTTPStatus.BAD_REQUEST
        if ret_value == HTTPStatus.OK:
            try:
                DB_TABLE = self.ImageMngDynamoDbResource.Table(self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME)
                TABLE_RESULTS:list[dict] = DB_TABLE.query(KeyConditionExpression=Key(cCommonFunc.API_RESP_DICT_KEY_ID).eq(ID))
                ITEMS:list[dict] = TABLE_RESULTS.get('Items', [])
                DATA:dict = ITEMS[0] if not cCommonFunc.is_none_or_empty(ITEMS) else {}
                SRC_URL = DATA.get(cCommonFunc.API_RESP_DICT_KEY_URL, "")
                # 署名付きURL(画像ダウンロード用)をAPI応答内容dictに設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=self._get_signed_url(S3_CLIENT=self.S3_CLIENT, CLIENT_METHOD='get_object', EXPIRATION=EXPIRATION, OBJECT_KEY=SRC_URL), KEY=cCommonFunc.API_RESP_DICT_KEY_URL)
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, ID:{ID}, EXPIRATION:{EXPIRATION}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
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
        ret_value = HTTPStatus.OK if self._is_exist_id_in_dynamodb_image_mng_table(ID=ID) else HTTPStatus.BAD_REQUEST
        if ret_value == HTTPStatus.OK:
            try:
                KEY_SRC_CONVERTIBLE = '#attr_convertible'
                KEY_DST_CONVERTIBLE = ':newConvertible'
                DB_TABLE = self.ImageMngDynamoDbResource.Table(self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME)
                OPTION = {
                    'Key': {cCommonFunc.API_RESP_DICT_KEY_ID:ID},
                    'ExpressionAttributeNames': {KEY_SRC_CONVERTIBLE:cCommonFunc.API_RESP_DICT_KEY_CONVERTIBLE},
                    'ExpressionAttributeValues': {f'{KEY_DST_CONVERTIBLE}': eImageConvertibleKind.get_value_from_name(NAME=CONVERTIBLE)},
                    'UpdateExpression': f'set {KEY_SRC_CONVERTIBLE} = {KEY_DST_CONVERTIBLE}'
                }
                DB_TABLE.update_item(**OPTION)
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, ID:{ID}, CONVERTIBLE:{CONVERTIBLE}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        else:
            # リクエストデータに不正がある旨をAPI処理結果詳細に設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'ID is not exist in table!\n\tID:{ID}')
        self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, ID:{ID}, CONVERTIBLE:{CONVERTIBLE}, ret_value:{ret_value}', PREFIX='::Leave')
        return ret_value

    def putitem_to_dynamodb_image_mng_table(self, FILE_URL:str, LAST_MODIFIED:str, API_RESULT_DATAS:dict[str, str], id:str = None, CONVERTIBLE:eImageConvertibleKind = eImageConvertibleKind.UNDETERMINED, dynamo_table = None) -> int:
        """AWS DynamoDBの画像IDと画像URL管理テーブルにアイテムを追加

        Args:
            FILE_URL (str): 画像URL
            LAST_MODIFIED (str): 最終更新日時
            API_RESULT_DATAS (dict[str, str]): API応答内容dict
            id (str, optional): 画像ID. Defaults to None.
            CONVERTIBLE (eImageConvertibleKind, optional): 画像フォーマット変換状態. Defaults to eImageConvertibleKind.UNDETERMINED.
            dynamo_table (_type_, optional): DynamoDBの画像IDと画像URL管理テーブルのインスタンス. Defaults to None.

        Returns:
            int: httpステータスコード
        """
        ret_value = HTTPStatus.OK if not self.ImageMngDynamoDbResource is None and not cCommonFunc.is_none_or_empty(FILE_URL) else HTTPStatus.INTERNAL_SERVER_ERROR
        if ret_value == HTTPStatus.OK:
            try:
                if id is None: id = str(uuid4())
                if dynamo_table is None: dynamo_table = self.ImageMngDynamoDbResource.Table(self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME)
                ITEM = {cCommonFunc.API_RESP_DICT_KEY_ID:id, cCommonFunc.API_RESP_DICT_KEY_URL:FILE_URL, cCommonFunc.API_RESP_DICT_KEY_LAST_MODIFIED:LAST_MODIFIED, cCommonFunc.API_RESP_DICT_KEY_CONVERTIBLE:CONVERTIBLE}
                dynamo_table.put_item(Item=ITEM)
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, FILE_URL:{FILE_URL}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value

    def _create_dynamo_db_table(self, DB_RESOURCE, TABLE_NAME:str = '', KEY_SCHEMA:list[dict] = [], ATTRIBUTE_DEFINITIONS:list[dict] = [], PROVISIONED_THROUGHPUT:dict[str, int] = {}) -> bool:
        """AWS SynamoDBのテーブル作成

        Args:
            DB_RESOURCE (_type_): AWS DynamoDBリソースのインスタンス
            TABLE_NAME (str, optional): DynamoDBテーブル名. Defaults to ''.
            KEY_SCHEMA (list[dict], optional): キースキーマ. Defaults to [].
            ATTRIBUTE_DEFINITIONS (list[dict], optional): 属性. Defaults to [].
            PROVISIONED_THROUGHPUT (dict[str, int], optional): テーブルのスループット. Defaults to {}.

        Returns:
            bool: 成功時はTrue、それ以外はFalse
        """
        ret_value = not DB_RESOURCE is None and not KEY_SCHEMA is None and not ATTRIBUTE_DEFINITIONS is None and not PROVISIONED_THROUGHPUT is None
        # DBテーブルが不存在
        if ret_value and not self._is_exist_dynamodb_table(TABLE_NAME=TABLE_NAME):
            try:
                TABLE = DB_RESOURCE.create_table(TableName=TABLE_NAME, KeySchema=KEY_SCHEMA, AttributeDefinitions=ATTRIBUTE_DEFINITIONS, ProvisionedThroughput=PROVISIONED_THROUGHPUT)
                # テーブルが作成されるまで待つ
                TABLE.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
            except Exception as e:
                ret_value = False
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, TABLE_NAME:{TABLE_NAME}, KEY_SCHEMA:{KEY_SCHEMA}, ATTRIBUTE_DEFINITIONS:{ATTRIBUTE_DEFINITIONS}, PROVISIONED_THROUGHPUT:{PROVISIONED_THROUGHPUT}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value

    def _is_exist_dynamodb_table(self, TABLE_NAME:str) -> bool:
        """DynamoDBに指定したテーブルが存在するか

        Args:
            TABLE_NAME (str): DynamoDBテーブル名

        Returns:
            bool: DynamoDBに指定したテーブルが存在する場合はTrue
        """
        ret_value = not self.DynamoDBClient is None and not cCommonFunc.is_none_or_empty(TABLE_NAME)
        if ret_value:
            try:
                TABLES:dict = self.DynamoDBClient.list_tables()
                ret_value = (TABLE_NAME in TABLES.get('TableNames', []))
            except Exception as e:
                ret_value = False
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, TABLE_NAME:{TABLE_NAME}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value

    def _set_image_url_hash_table_from_db(self, IMAGE_HASH_TABLES:list[dict[str, str|int]]) -> bool:
        """DBから画像ID・画像変換状態・画像URLのhash-tableリスト設定

        Args:
            IMAGE_HASH_TABLES (list[dict[str, str | int]]): 画像ID・画像変換状態・画像URLのhash-tableリスト

        Returns:
            bool: 成功時はTrue、それ以外はFalse
        """
        ret_value = not IMAGE_HASH_TABLES is None
        # hash-tableリストクリア
        if not IMAGE_HASH_TABLES is None: IMAGE_HASH_TABLES.clear()
        # 管理DB(画像IDとURL)が存在する
        if ret_value and self._is_exist_dynamodb_table(TABLE_NAME=self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME):
            try:
                PAGINATOR = self.DynamoDBClient.get_paginator('scan')
                for PAGE in PAGINATOR.paginate(TableName=self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME):
                    for PAGE_ITEM in PAGE.get('Items', {}):
                        ITEM = {k:self.Deserializer.deserialize(v) for k, v in PAGE_ITEM.items()}
                        IMAGE_HASH_TABLES.append(ITEM)
            except Exception as e:
                ret_value = False
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, len(IMAGE_HASH_TABLES):{len(IMAGE_HASH_TABLES)}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
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
                '''
                OBJECTSのデータ例:
                {
                    'ResponseMetadata':
                    {
                        (レスポンスの定義情報)
                    },
                    'IsTruncated': False,
                    'Marker': '',
                    'Contents': [
                        {
                            'Key': '(ファイルパス)',
                            'LastModified': datetime.datetime(2024, 5, 30, 3, 40, 35, tzinfo=tzlocal()),
                            'ETag': '"～"',
                            'Size': (ファイルサイズ),
                            'StorageClass': 'STANDARD',
                            'Owner':
                            {
                                'DisplayName': 'webfile',
                                'ID': '～'
                            }
                        },
                        ...
                    ],
                    'Name': '(S3バケット名 ※"self.S3_BUCKET_NAME"の値)',
                    'Prefix': '(プレフィックス ※"self.S3_PREFIX"の値)',
                    'MaxKeys': 1000,
                    'EncodingType': 'url'
                }
                '''
                for CONTENT in OBJECTS.get('Contents', []):
                    if 'Key' in CONTENT and CONTENT.get('Size', -1) > 0:
                        IMAGE_FILE_PATHS.append({cCommonFunc.API_RESP_DICT_KEY_URL:CONTENT['Key'], cCommonFunc.API_RESP_DICT_KEY_LAST_MODIFIED:CONTENT.get("LastModified", "")})
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'len(IMAGE_FILE_PATHS):{len(IMAGE_FILE_PATHS)}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        self.LOGGER_WRAPPER.output(MSG=f'len(IMAGE_FILE_PATHS):{len(IMAGE_FILE_PATHS)}, ret_value:{ret_value}', PREFIX='::Leave')
        return ret_value

    def _append_hash_tables_from_s3(self, API_RESULT_DATAS:dict[str, str], S3_IMAGE_FILE_PATH_DICTS:list[dict]) -> tuple[int, list[dict[str, str|int]]]:
        """画像ID・画像変換状態・画像URLのhash-tableリストにS3画像ファイルパスからテーブルを追加

        Args:
            API_RESULT_DATAS (dict[str, str]): API応答内容dict
            S3_IMAGE_FILE_PATHS (list[dict]): AWS S3内画像ファイルパスと最終更新日時リスト

        Returns:
            tuple[int, list[dict[str, str|int]]]: [0]:httpステータスコード, [1]:画像ID・画像変換状態・画像URLのhash-tableリスト
        """
        ret_value = HTTPStatus.OK if not S3_IMAGE_FILE_PATH_DICTS is None else HTTPStatus.INTERNAL_SERVER_ERROR

        image_hash_table:list[dict[str, str|int]] = []
        # 引数正常 かつ DBからデータ取得成功
        if ret_value == HTTPStatus.OK and self._set_image_url_hash_table_from_db(IMAGE_HASH_TABLES=image_hash_table):
            try:
                FILE_PATHS:list[str] = []
                for FILE_PATH_DICT in S3_IMAGE_FILE_PATH_DICTS:
                    FILE_PATH:str = FILE_PATH_DICT.get(cCommonFunc.API_RESP_DICT_KEY_URL, "")
                    FILE_PATHS.append(FILE_PATH)
                    LAST_MODIFIED = FILE_PATH_DICT.get(cCommonFunc.API_RESP_DICT_KEY_LAST_MODIFIED, datetime.min)
                    # hash-tableに存在しない画像ファイルパスの場合
                    if not self._is_exist_value_in_hash_table(IMAGE_HASH_TABLE=image_hash_table, KEY=cCommonFunc.API_RESP_DICT_KEY_URL, DST_VALUE=FILE_PATH):
                        TABLE:dict[str, str] = {}
                        TABLE[cCommonFunc.API_RESP_DICT_KEY_ID] = str(uuid4())
                        TABLE[cCommonFunc.API_RESP_DICT_KEY_URL] = FILE_PATH
                        TABLE[cCommonFunc.API_RESP_DICT_KEY_LAST_MODIFIED] = LAST_MODIFIED.strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]
                        TABLE[cCommonFunc.API_RESP_DICT_KEY_CONVERTIBLE] = eImageConvertibleKind.UNDETERMINED
                        image_hash_table.append(TABLE)
                # S3バケット内に存在するファイルのみ残す
                image_hash_table = [i for i in image_hash_table if i.get(cCommonFunc.API_RESP_DICT_KEY_URL, '') in FILE_PATHS]
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, len(API_RESULT_DATAS):{-1 if API_RESULT_DATAS is None else len(API_RESULT_DATAS)}, len(S3_IMAGE_FILE_PATH_DICTS):{-1 if S3_IMAGE_FILE_PATH_DICTS is None else len(S3_IMAGE_FILE_PATH_DICTS)}, len(image_hash_table):{-1 if image_hash_table is None else len(image_hash_table)}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        else:
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'hash-tables is None or parameter is invalid!\n, len(S3_IMAGE_FILE_PATHS):{-1 if S3_IMAGE_FILE_PATH_DICTS is None else len(S3_IMAGE_FILE_PATH_DICTS)}')

        return ret_value, image_hash_table

    def _force_update_db_from_hash_table(self, API_RESULT_DATAS:dict[str, str], IMAGE_HASH_TABLE:list[dict[str, str|int]]) -> int:
        """画像IDと画像URL管理DB強制更新(※DBが存在しない場合は新規作成)

        Args:
            API_RESULT_DATAS (dict[str, str]): API応答内容dict
            IMAGE_HASH_TABLE (list[dict[str, str | int]]): 画像ID・画像変換状態・画像URLのhash-tableリスト

        Returns:
            int: httpステータスコード
        """
        # ※テーブルを一旦削除する
        ret_value = HTTPStatus.OK if not IMAGE_HASH_TABLE is None and self._delete_dynamodb_table_items(TABLE_NAME=self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME) and not self.ImageMngDynamoDbResource is None else HTTPStatus.INTERNAL_SERVER_ERROR
        if ret_value == HTTPStatus.OK:
            try:
                DYNAMO_TABLE = self.ImageMngDynamoDbResource.Table(self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME)
                PUT_RESULTS:list[int] = []
                for TABLE in IMAGE_HASH_TABLE:
                    PUT_RESULTS.append(self.putitem_to_dynamodb_image_mng_table(FILE_URL=TABLE.get(cCommonFunc.API_RESP_DICT_KEY_URL, ''), LAST_MODIFIED=TABLE.get(cCommonFunc.API_RESP_DICT_KEY_LAST_MODIFIED, datetime.min.strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]), CONVERTIBLE=TABLE.get(cCommonFunc.API_RESP_DICT_KEY_CONVERTIBLE, eImageConvertibleKind.UNDETERMINED), API_RESULT_DATAS=API_RESULT_DATAS, id=TABLE.get(cCommonFunc.API_RESP_DICT_KEY_ID, str(uuid4())), dynamo_table=DYNAMO_TABLE))
                ret_value = max(PUT_RESULTS)
            except Exception as e:
                ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
                # 例外内容をAPI処理結果詳細に設定
                cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        else:
            # 内部変数に不正がある旨をAPI処理結果詳細に設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'hash-tables is None or internal parameter is invalid!, len(self.S3_BUCKET_NAME):{len(self.S3_BUCKET_NAME)}, len(self.S3_DB_NAME):{len(self.S3_DB_NAME)}')
        return ret_value

    def _delete_dynamodb_table_items(self, TABLE_NAME:str) -> bool:
        """AWS DynamoDBのテーブル内アイテム全削除

        Args:
            TABLE_NAME (str): テーブル名

        Returns:
            bool: 成功時はTrue、それ以外はFalse
        """
        ret_value = not cCommonFunc.is_none_or_empty(TABLE_NAME)
        # テーブルが存在する
        if ret_value and self._is_exist_dynamodb_table(TABLE_NAME=TABLE_NAME) and not self.ImageMngDynamoDbResource is None:
            try:
                DELETE_ITEMS:list[dict] = []
                PAGINATOR = self.DynamoDBClient.get_paginator('scan')
                for PAGE in PAGINATOR.paginate(TableName=self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME):
                    DELETE_ITEMS.extend(PAGE.get('Items', {}))

                DYNAMO_TABLE = self.ImageMngDynamoDbResource.Table(self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME)
                KEY_NAMES = [ x.get('AttributeName', "") for x in DYNAMO_TABLE.key_schema ]
                DELETE_KEYS = [ { k:v for k,v in x.items() if k in KEY_NAMES } for x in DELETE_ITEMS ]

                with DYNAMO_TABLE.batch_writer() as BATCH:
                    for DEL_KEY in DELETE_KEYS:
                        for KEY, VALUE in DEL_KEY.items():
                            BATCH.delete_item(Key = {KEY:self.Deserializer.deserialize(VALUE)})
            except Exception as e:
                ret_value = False
                self.LOGGER_WRAPPER.output(MSG=f'self:{self}, TABLE_NAME:{TABLE_NAME}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value

    def _is_exist_id_in_dynamodb_image_mng_table(self, ID:str) -> bool:
        """指定したIDがDynamoDBの「画像IDとURL管理テーブル」に存在するか

        Args:
            ID (str): 画像ID

        Returns:
            bool: 指定したIDがDynamoDBの「画像IDとURL管理テーブル」に存在する場合はTrue、それ以外はFalse
        """
        ret_value = not self.ImageMngDynamoDbResource is None
        if ret_value:
            try:
                TABLE = self.ImageMngDynamoDbResource.Table(self.DYNAMO_DB_IMAGE_MNG_TABLE_NAME)
                RESPONSE:dict = TABLE.query(KeyConditionExpression=Key(cCommonFunc.API_RESP_DICT_KEY_ID).eq(ID))
                COUNT = RESPONSE.get('Count', 0)
                ret_value = COUNT > 0
            except Exception as e:
                ret_value = False
                self.LOGGER_WRAPPER.output(MSG=f'self:<{self}>, ID:{ID}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value

    def _is_exist_value_in_hash_table(self, IMAGE_HASH_TABLE:list[dict[str, str|int]], KEY:str, DST_VALUE:str) -> bool:
        """hash-tableの該当keyに値が存在するかチェック

        Args:
            IMAGE_HASH_TABLE (list[dict[str, str | int]]): 画像ID・画像変換状態・画像URLのhash-tableリスト
            KEY (str): hash-tableキー名
            DST_VALUE (str): 検索対象値

        Returns:
            bool: hash-tableの該当keyに値が存在する場合はTrue、それ以外はFalse
        """
        ret_value = not IMAGE_HASH_TABLE is None
        if ret_value:
            try:
                ret_value = any(DST_VALUE == HASH_TABLE.get(KEY, '') for HASH_TABLE in IMAGE_HASH_TABLE)
            except Exception as e:
                ret_value = False
                self.LOGGER_WRAPPER.output(MSG=f'len(IMAGE_HASH_TABLE):{len(IMAGE_HASH_TABLE)}, KEY:{KEY}, DST_VALUE:{DST_VALUE}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
        return ret_value
