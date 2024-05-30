"""S3へのオブジェクトアップロードイベントハンドラ
"""
import dateutil.parser as du_parser
import logging

from http import HTTPStatus
from module.aws_mng import cAwsAccessMng
from module.common_func import cCommonFunc
from module.env_mng import cEnvMng
from module.logger_wrapper import cLoggerWrapper

ENV_MNG = cEnvMng()
LOGGER_WRAPPER:cLoggerWrapper = cLoggerWrapper(LEVEL=ENV_MNG.LOG_LEVEL)
AWS_MNG = cAwsAccessMng(REGION_NAME=ENV_MNG.AWS_REGION, S3_BUCKET=ENV_MNG.AWS_S3_BUCKET, DYNAMO_DB_IMAGE_MNG_TABLE_NAME=ENV_MNG.AWS_DYNAMODB_IMAGE_MNG_TABLE_NAME, LOGGER_WRAPPER=LOGGER_WRAPPER)
AWS_MNG.initialize()
DICT_KEY_TIME = 'time'
DICT_KEY_FILE_NAME = 'file_name'

def lambda_handler(event, context):
    LOGGER_WRAPPER.output(MSG=f'', PREFIX='::Enter')
    RESULT_DATAS:dict[str, str] = {cCommonFunc.API_RESP_DICT_KEY_RESULT:''}
    S3_OBJECT_DATAS:list[str] = [] # イベント内のS3オブジェクトの日時・ファイル名リスト
    # S3オブジェクトの日時・ファイル名リストを設定
    status = get_s3_event_object_keys(RECORDS=event.get('Records', []), S3_OBJECT_DATAS=S3_OBJECT_DATAS, API_RESULT_DATAS=RESULT_DATAS)
    # S3オブジェクトの日時・ファイル名リスト設定成功
    if status == HTTPStatus.OK:
        # DB更新処理呼び出し
        status = call_update_db_func(S3_OBJECT_DATAS=S3_OBJECT_DATAS, API_RESULT_DATAS=RESULT_DATAS)
    LOGGER_WRAPPER.output(MSG=f'status:{status}, RESULT_DATAS:{RESULT_DATAS}', PREFIX='::Leave')
    return RESULT_DATAS, status

def get_s3_event_object_keys(RECORDS:list[dict[str, str|dict]], S3_OBJECT_DATAS:list[dict], API_RESULT_DATAS:dict[str, str]) -> int:
    """S3オブジェクトの日時・ファイル名リストを設定

    Args:
        RECORDS (list[dict[str, str | dict]]): レコード(lambda_handlerのイベント)
        S3_OBJECT_DATAS (list[dict]): S3オブジェクトの日時・ファイル名リスト
        API_RESULT_DATAS (dict[str, str]): 応答内容dict

    Returns:
        int: httpステータスコード
    """
    LOGGER_WRAPPER.output(MSG=f'len(RECORDS):{-1 if RECORDS is None else len(RECORDS)}', PREFIX='::Enter')
    ret_value = HTTPStatus.OK if not cCommonFunc.is_none_or_empty(RECORDS) and not S3_OBJECT_DATAS is None else HTTPStatus.INTERNAL_SERVER_ERROR
    if ret_value == HTTPStatus.OK:
        try:
            S3_OBJECT_DATAS.clear()
            for RECORD in RECORDS:
                EVENT_TIME:str = RECORD.get('eventTime', "")
                S3_OBJECT:dict = RECORD.get('s3', {}).get('object', {})
                if 'key' in S3_OBJECT and not cCommonFunc.is_none_or_empty(EVENT_TIME):
                    S3_OBJECT_DATAS.append({DICT_KEY_FILE_NAME:S3_OBJECT.get('key'), DICT_KEY_TIME:du_parser.parse(EVENT_TIME).strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]})
        except Exception as e:
            ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
            # 例外内容をAPI処理結果詳細に設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
            LOGGER_WRAPPER.output(MSG=f'len(RECORDS):{-1 if RECORDS is None else len(RECORDS)}, len(S3_OBJECT_DATAS):{-1 if S3_OBJECT_DATAS is None else len(S3_OBJECT_DATAS)}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
    LOGGER_WRAPPER.output(MSG=f'len(RECORDS):{-1 if RECORDS is None else len(RECORDS)}, len(S3_OBJECT_DATAS):{-1 if S3_OBJECT_DATAS is None else len(S3_OBJECT_DATAS)}, ret_value:{ret_value}', PREFIX='::Leave')
    return ret_value

def call_update_db_func(S3_OBJECT_DATAS:list[dict], API_RESULT_DATAS:dict[str, str]) -> int:
    """DB更新処理呼び出し

    Args:
        S3_OBJECT_DATAS (list[dict]): S3オブジェクトの日時・ファイル名リスト
        API_RESULT_DATAS (dict[str, str]): 応答内容dict

    Returns:
        int: httpステータスコード
    """
    LOGGER_WRAPPER.output(MSG=f'len(S3_OBJECT_DATAS):{-1 if S3_OBJECT_DATAS is None else len(S3_OBJECT_DATAS)}', PREFIX='::Enter')
    ret_value = HTTPStatus.OK if not S3_OBJECT_DATAS is None and not AWS_MNG is None else HTTPStatus.INTERNAL_SERVER_ERROR
    if ret_value == HTTPStatus.OK:
        try:
            PUT_RESULTS:list[int] = []
            for OBJECT in S3_OBJECT_DATAS:
                PUT_RESULTS.append(AWS_MNG.putitem_to_dynamodb_image_mng_table(FILE_URL=OBJECT.get(DICT_KEY_FILE_NAME, ''), LAST_MODIFIED=OBJECT.get(DICT_KEY_TIME, ''), API_RESULT_DATAS=API_RESULT_DATAS))
            ret_value = max(PUT_RESULTS)
        except Exception as e:
            ret_value = HTTPStatus.INTERNAL_SERVER_ERROR
            # 例外内容をAPI処理結果詳細に設定
            cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=API_RESULT_DATAS, VALUE=f'{type(e).__name__}, {e}')
            LOGGER_WRAPPER.output(MSG=f'len(S3_OBJECT_DATAS):{-1 if S3_OBJECT_DATAS is None else len(S3_OBJECT_DATAS)}, {type(e).__name__}! {e}', LEVEL=logging.WARN)
    LOGGER_WRAPPER.output(MSG=f'len(S3_OBJECT_DATAS):{-1 if S3_OBJECT_DATAS is None else len(S3_OBJECT_DATAS)}, ret_value:{ret_value}', PREFIX='::Leave')
    return ret_value
