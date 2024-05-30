from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from http import HTTPStatus
from module.aws_mng import cAwsAccessMng
from module.common_func import cCommonFunc
from module.env_mng import cEnvMng
from module.logger_wrapper import cLoggerWrapper

ENV_MNG = cEnvMng()
LOGGER_WRAPPER:cLoggerWrapper = cLoggerWrapper(LEVEL=ENV_MNG.LOG_LEVEL)
AWS_MNG = cAwsAccessMng(REGION_NAME=ENV_MNG.AWS_REGION, S3_BUCKET=ENV_MNG.AWS_S3_BUCKET, DYNAMO_DB_IMAGE_MNG_TABLE_NAME=ENV_MNG.AWS_DYNAMODB_IMAGE_MNG_TABLE_NAME, LOGGER_WRAPPER=LOGGER_WRAPPER)
app = APIGatewayRestResolver()

@app.post("/signed_url")
def get_signedurl() -> tuple[dict[str, str|list], int]:
    """署名付きURL取得要求

    Returns:
        tuple[dict[str, str|list], int]: [0]:応答内容dict(ex:{'result':'OK', 'signed_urls':[{'src.png':'http://～'}, ...]}), [1]:ステータスコード
    """
    LOGGER_WRAPPER.output(f'', PREFIX='::Enter')
    JSON_DATA:dict = {} if app.current_event is None or not hasattr(app.current_event, 'json_body') else app.current_event.json_body
    IMAGE_FILE_PATHS:list[str] = JSON_DATA.get('images', [])

    RESULT_DATAS:dict[str, str|list] = {cCommonFunc.API_RESP_DICT_KEY_RESULT:'', cCommonFunc.API_RESP_DICT_KEY_SIGNED_URLS:[]}
    STATUS = AWS_MNG.get_signed_urls_for_put_object(IMAGE_FILE_PATHS=IMAGE_FILE_PATHS, API_RESULT_DATAS=RESULT_DATAS)
    _set_api_result_msg(STATUS_CODE=STATUS, RESULT_DATAS=RESULT_DATAS)
    LOGGER_WRAPPER.output(f'RESULT_DATAS:{RESULT_DATAS}, STATUS:{STATUS}', PREFIX='::Leave')
    return RESULT_DATAS, STATUS

@app.get("/update_table")
def update_table() -> tuple[dict[str, str], int]:
    """テーブル更新要求

    Returns:
        tuple[dict[str, str], int]: [0]:応答内容dict(ex:{'result':'OK'}), [1]:ステータスコード
    """
    LOGGER_WRAPPER.output(f'', PREFIX='::Enter')
    RESULT_DATAS:dict[str, str] = {cCommonFunc.API_RESP_DICT_KEY_RESULT:''}
    STATUS = AWS_MNG.force_update_image_mng_hash_table(API_RESULT_DATAS=RESULT_DATAS)
    _set_api_result_msg(STATUS_CODE=STATUS, RESULT_DATAS=RESULT_DATAS)
    LOGGER_WRAPPER.output(f'RESULT_DATAS:{RESULT_DATAS}, STATUS:{STATUS}', PREFIX='::Leave')
    return RESULT_DATAS, STATUS

@app.get("/images")
@app.get("/images/<COUNT>")
def get_images(COUNT:int = 0) -> tuple[dict[str, str|list], int]:
    """画像リスト要求

    Args:
        COUNT (int, optional): 取得する画像リスト数(0の場合は全件取得). Defaults to 0.

    Returns:
        tuple[dict[str, str|list], int]: [0]:応答内容dict(ex:{'result':'OK', 'data':[{'id':'abcd...', 'convertible':'undetermined', 'url':'http://～'}, ...]}), [1]:ステータスコード
    """
    LOGGER_WRAPPER.output(f'COUNT:{COUNT}', PREFIX='::Enter')
    RESULT_DATAS:dict[str, str|list] = {cCommonFunc.API_RESP_DICT_KEY_RESULT:'', cCommonFunc.API_RESP_DICT_KEY_DATA:[]}
    STATUS = AWS_MNG.get_images(COUNT=COUNT, API_RESULT_DATAS=RESULT_DATAS)
    _set_api_result_msg(STATUS_CODE=STATUS, RESULT_DATAS=RESULT_DATAS)
    LOGGER_WRAPPER.output(f'COUNT:{COUNT}, RESULT_DATAS.{cCommonFunc.API_RESP_DICT_KEY_RESULT}:{RESULT_DATAS.get(cCommonFunc.API_RESP_DICT_KEY_RESULT, "")}, len(RESULT_DATAS.{cCommonFunc.API_RESP_DICT_KEY_DATA}):{len(RESULT_DATAS.get(cCommonFunc.API_RESP_DICT_KEY_DATA, []))}, STATUS:{STATUS}', PREFIX='::Leave')
    return RESULT_DATAS, STATUS

@app.get("/image/<ID>")
def get_image(ID:str) -> tuple[dict[str, str], int]:
    """画像要求

    Args:
        ID (str): 画像ID

    Returns:
        tuple[dict[str, str], int]: [0]:応答内容dict(ex:{'result':'OK', 'url':'http://～'}), [1]:ステータスコード
    """
    LOGGER_WRAPPER.output(f'ID:{ID}', PREFIX='::Enter')
    RESULT_DATAS:dict[str, str] = {cCommonFunc.API_RESP_DICT_KEY_RESULT:'', cCommonFunc.API_RESP_DICT_KEY_URL:''}
    STATUS = AWS_MNG.get_signed_urls_for_get_object_to_id(ID=ID, API_RESULT_DATAS=RESULT_DATAS)
    _set_api_result_msg(STATUS_CODE=STATUS, RESULT_DATAS=RESULT_DATAS)
    LOGGER_WRAPPER.output(f'ID:{ID}, RESULT_DATAS:{RESULT_DATAS}, STATUS:{STATUS}', PREFIX='::Leave')
    return RESULT_DATAS, STATUS

@app.patch("/image/<ID>")
def update_image_data(ID:str) -> tuple[dict[str, str], int]:
    """画像情報更新

    Args:
        ID (str): 画像ID

    Returns:
        tuple[dict[str, str], int]: [0]:応答内容dict(ex:{'result':'OK'}), [1]:ステータスコード
    """
    LOGGER_WRAPPER.output(f'ID:{ID}', PREFIX='::Enter')
    JSON_DATA:dict = {} if app.current_event is None or not hasattr(app.current_event, 'json_body') else app.current_event.json_body
    CONVERTIBLE:str = JSON_DATA.get('convertible', '')
    RESULT_DATAS:dict[str, str] = {cCommonFunc.API_RESP_DICT_KEY_RESULT:''}
    STATUS = AWS_MNG.update_hash_table_image_convertible_state(ID=ID, CONVERTIBLE=CONVERTIBLE, API_RESULT_DATAS=RESULT_DATAS)
    _set_api_result_msg(STATUS_CODE=STATUS, RESULT_DATAS=RESULT_DATAS)
    LOGGER_WRAPPER.output(f'ID:{ID}, RESULT_DATAS:{RESULT_DATAS}, STATUS:{STATUS}', PREFIX='::Leave')
    return RESULT_DATAS, STATUS

def _set_api_result_msg(STATUS_CODE:int, RESULT_DATAS:dict[str, str]) -> bool:
    """API応答内容dictの"API処理結果"にメッセージを設定

    Args:
        STATUS_CODE (int): httpステータスコード
        RESULT_DATAS (dict[str, str]): API応答内容dict

    Returns:
        bool: 成功時はTrue、それ以外はFalse
    """
    return cCommonFunc.set_api_resp_str_msg(API_RESULT_DATAS=RESULT_DATAS, VALUE='OK' if STATUS_CODE==HTTPStatus.OK else 'NG', KEY=cCommonFunc.API_RESP_DICT_KEY_RESULT)

def lambda_handler(event, context) -> dict[str, type]:
    """AWS Lambdaハンドラ関数

    Args:
        event (_type_): Lambda関数の呼び出し元の情報
        context (_type_): コンテキストオブジェクト(呼び出し、関数、および実行関数に関する情報を示すメソッドおよびプロパティ)

    Returns:
        dict[str, type]: _description_
    """
    RESULT = app.resolve(event, context)
    return RESULT
