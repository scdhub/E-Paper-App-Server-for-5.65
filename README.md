# E-Paper-App-Server-for-5.65
5.65Epaper向けアプリサーバAPIソース
<!-- シールド一覧 -->
<p style="display: inline">
    <img src="https://img.shields.io/badge/-Python-F2C63C.svg?logo=python&style=flat">
    <img src="https://img.shields.io/badge/-Amazon%20aws-232F3E.svg?logo=amazon-aws&style=flat">
    <img src="https://img.shields.io/badge/-Visual%20Studio%20Code-007ACC.svg?logo=visual-studio-code&style=flat">
    <img src="https://img.shields.io/badge/-Docker-EEE.svg?logo=docker&style=flat">
    <img src="https://img.shields.io/badge/PlantUML-blueviolet.svg?style=flat">
</p>

## 目次

1. [ディレクトリ構成](#ディレクトリ構成)
1. [環境構築～AWSデプロイ](#環境構築awsデプロイ)
1. [API仕様](#api仕様)
1. [トラブルシューティング](#トラブルシューティング)

## ディレクトリ構成
<pre>
.
├bat
│└(※ビルドおよびデプロイ用のバッチファイル集)
├src
│├module
││└(※app.py, s3_object_put_handler.pyが参照する自作モジュール格納フォルダ)
│├app.py ※API実行Lambda関数の実装
│├requirements.txt
│├s3_object_put_handler.py ※S3からの通知を受け取るLambda関数の実装
│├samconfig.toml
│└template.yaml
├uml ※PlantUMLを使用したUML図格納フォルダ
│├sequence
││└ESL_sequence.pu ※シーケンス図
│└usecase
│  └ESL_usecase.pu ※ユースケース図
├_create_env.bat ※デプロイ環境構築用bat
└README.md ※このファイル
</pre>

<p align="right">(<a href="#top">トップへ</a>)</p>

## 環境構築～AWSデプロイ
※AWSデプロイを行う際は環境構築を先に行う必要がある。</br>

### 1.環境構築

#### Pythonインストール
[Pythonのインストールを行う。](https://www.python.org/downloads/)

#### ライブラリのインストールおよびPython仮想環境の起動
ルートフォルダ配下の"_create_env.bat"を実行する</br>
→本batを実行することで、デプロイに必要なライブラリのインストールおよびPython仮想環境の起動が行われる。</br>

<p align="right">(<a href="#top">トップへ</a>)</p>

---


### 2.AWSデプロイ
#### 認証情報の設定
下記の手順で認証情報の設定を行う</br>
※AWSアカウントおよびIAMユーザは作成済みであることを前提とする。
1. [IAM ユーザーの認証情報(アクセスキーID・シークレットアクセスキー)を発行する](https://docs.aws.amazon.com/ja_jp/IAM/latest/UserGuide/id_credentials_access-keys.html)
1. [AWS CLI をインストールする](https://docs.aws.amazon.com/ja_jp/cli/latest/userguide/cli-configure-files.html)
1. [AWS CLI に IAM ユーザーの認証情報を設定する](https://docs.aws.amazon.com/ja_jp/cli/latest/userguide/cli-configure-files.html)

#### Dockerインストール
[Dockerのインストールを行う。](https://docs.aws.amazon.com/ja_jp/serverless-application-model/latest/developerguide/install-docker.html)

#### デプロイ手順
※(Python仮想環境を立ち上げていない場合、)ルートフォルダでコマンドラインを起動し、下記コマンドでPython仮想環境を起動する。
```dos
.venv\Scripts\activate.bat
```

1. Python仮想環境起動状態で、ルートフォルダから下記コマンドを実行する。
```dos
bat\_aws_sam_deploy.bat
```

2. 実行が成功した場合、コマンドラインに下記のような表示がされ、</br>
<span style="color: red; ">Value</span>に表示されているURLがAPIのルートURLとなる。
```
(略)
CloudFormation outputs from deployed stack
---------------------------------------------------------------------------------------------------------------------
Outputs
---------------------------------------------------------------------------------------------------------------------
Key                 FunctionUrl
Description         API Root URL
Value               https://***.execute-api.(リージョン).amazonaws.com/(ステージ)/
---------------------------------------------------------------------------------------------------------------------
Successfully created/updated stack - Epaper-apl-server-apim in (リージョン)
```

#### AWSスタック一覧
デプロイ成功時にAWSに作成されるスタックは下記のとおりである。</br>
| タイプ | リソースID | 概要 |
| :--- | :--- | :--- |
| AWS::IAM::Role | LambdaIAMRole | Lambda関数のIAMロール</br>S3・DynamoDB・LogStreamへのアクセス権を付与している |
| AWS::Lambda::Function | ApiLambdaFunction | API実行Lambda関数</br>※実行内容:src/app.pyに実装 |
| AWS::Lambda::Permission | ApiLambdaFunctionApiProxyPermissionStage | API実行Lambda関数の使用許可 |
| AWS::Logs::LogGroup | FunctionLogGroup | API実行Lambda関数のロググループ |
| AWS::ApiGateway::Deployment | ApiGatewayRestApiDeployment(ID) | APIのバージョン |
| AWS::ApiGateway::RestApi | ApiGatewayRestApi | APIゲートウェイ(ApiLambdaFunctionを発火させる) |
| AWS::ApiGateway::Stage | ApiGatewayRestApiStage | エンドポイントのバージョン |
| AWS::ApiGateway::ApiKey | RestApiKey | 各APIアクセス時に必要なAPIキー |
| AWS::ApiGateway::UsagePlan | ApiUsagePlan | APIのリクエスト制限 |
| AWS::ApiGateway::UsagePlanKey | ApiUsagePlanKey | APIキーとUsagePlan(ApiUsagePlan)の紐づけ |
| AWS::Lambda::Function | S3NotificationLambdaFunction | S3からの通知を受け取るLambda関数</br>※実行内容:src/s3_object_put_handler.pyに実装 |
| AWS::Lambda::Permission | LambdaInvokePermission | S3からの通知を受け取るLambda関数(S3NotificationLambdaFunction)の使用許可 |
| AWS::Logs::LogGroup | S3NotificationLambdaFunctionLogGroup | S3からの通知を受け取るLambda関数(S3NotificationLambdaFunction)のロググループ |
| AWS::Lambda::Function | CustomResourceLambdaFunction | S3通知を設定するLambda関数</br>※実行内容:src/template.yamlに実装 |
| AWS::Logs::LogGroup | CustomResourceLambdaFunctionLogGroup | S3通知を設定するLambda関数のロググループ |
| Custom::LambdaTrigger | LambdaTrigger | S3通知の設定 |

<p align="right">(<a href="#top">トップへ</a>)</p>

---


### 3.【参考】デプロイした環境一式を削除したい場合
#### AWSマネジメントコンソールを使用する場合
1. AWSマネジメントコンソールから"CloudFormation"を選択する。
1. 「削除」ボタンをクリックする。

#### AWSマネジメントコンソールを使用しない場合
※(Python仮想環境を立ち上げていない場合、)ルートフォルダでコマンドラインを起動し、下記コマンドでPython仮想環境を起動する。
```dos
.venv\Scripts\activate.bat
```

Python仮想環境起動状態で、ルートフォルダから下記コマンドを実行する。
```dos
cd src
sam delete --no-prompts
```

<p align="right">(<a href="#top">トップへ</a>)</p>

## API仕様

### 1.署名付きURL取得

AWS S3ファイルアップロード用署名付きURLを取得する。</br></br>
URL : `/signed_url`</br>
メソッド : `POST`</br>
httpヘッダー :
```text
Content-Type: application/json
x-api-key: "APIキー"
```

リクエストデータ :
```json
{
    "images":
    [
      "アップロード対象の画像ファイルパス",
      ...
    ]
}
```

#### 正常応答
HTTPステータスコード : `200 OK`</br>
コンテンツ :
```json
{
    "result": "OK",
    "signed_urls":
    [
      {"(アップロード対象の画像ファイルパス)", "(画像アップロード用署名付きURL)"},
      ...
    ]
}
```

#### エラー応答
エラー内容 : APIキー未指定及びAPIキーエラー。</br>
ステータスコード : `403 Forbidden`</br>
コンテンツ :
```json
{
    "message": "Forbidden"
}
```
</br>

エラー内容 : リクエストデータが不正(画像ファイルパスリストが0件 or 未指定)。</br>
ステータスコード : `400 BAD REQUEST`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "The input image file path list is empty or there is no URL storage location. image file path list length is 0"
}
```
</br>

エラー内容 : サーバエラー。</br>
ステータスコード : `500 INTERNAL SERVER ERROR`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "エラー内容"
}
```

<p align="right">(<a href="#top">トップへ</a>)</p>

---


### 2.画像リスト要求

「画像IDと画像URL」のリストを取得する。</br></br>
URL : `/images`</br>
メソッド : `GET`</br>
httpヘッダー :
```text
x-api-key: "APIキー"
```
リクエストデータ : なし</br>

#### 正常応答
HTTPステータスコード : `200 OK`</br>
コンテンツ :
```json
{
    "result": "OK",
    "data": [
      {
        "id": "画像ID",
        "convertible": Epaper画像フォーマット変換可能状態(undetermined: 未判定, enabled: 変換可能, invalid: 変換不可),
        "last_modified" : "最終更新日時(ex: 2024/01/01 12:34:56)",
        "url": "画像ダウンロード用署名付きURL"
      }
    ]
}
```

#### エラー応答
エラー内容 : APIキー未指定及びAPIキーエラー。</br>
ステータスコード : `403 Forbidden`</br>
コンテンツ :
```json
{
    "message": "Forbidden"
}
```
</br>

エラー内容 : サーバエラー。</br>
ステータスコード : `500 INTERNAL SERVER ERROR`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "エラー内容"
}
```

<p align="right">(<a href="#top">トップへ</a>)</p>

---

### 3.画像リスト要求(範囲取得)

「画像IDと画像URL」のリストを範囲取得する。</br></br>
URL : `/images/count?START={int}&COUNT={int}`</br>
メソッド : `GET`</br>
httpヘッダー :
```text
x-api-key: "APIキー"
```
リクエストデータ : なし</br>

#### 正常応答
HTTPステータスコード : `200 OK`</br>
コンテンツ :
```json
{
    "result": "OK",
    "data": [
      {
        "id": "画像ID",
        "convertible": Epaper画像フォーマット変換可能状態(undetermined: 未判定, enabled: 変換可能, invalid: 変換不可),
        "last_modified" : "最終更新日時(ex: 2024/01/01 12:34:56)",
        "url": "画像ダウンロード用署名付きURL"
      }...
    ]
}
```

#### エラー応答
エラー内容 : APIキー未指定及びAPIキーエラー。</br>
ステータスコード : `403 Forbidden`</br>
コンテンツ :
```json
{
    "message": "Forbidden"
}
```
</br>

エラー内容 : リクエストデータが不正(クエリパラメータが不正)。</br>
ステータスコード : `400 BAD REQUEST`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "The query parameters are invalid."
}
```


エラー内容 : サーバエラー。</br>
ステータスコード : `500 INTERNAL SERVER ERROR`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "エラー内容"
}
```

<p align="right">(<a href="#top">トップへ</a>)</p>

---


### 4.画像要求
画像IDに対応する画像URLを取得する。</br></br>
URL : `/image/{id}`</br>
メソッド : `GET`</br>
httpヘッダー :
```text
x-api-key: "APIキー"
```
リクエストデータ : なし</br>

#### 正常応答
HTTPステータスコード : `200 OK`</br>
コンテンツ :
```json
{
    "result": "OK",
    "url": "画像ダウンロード用署名付きURL"
}
```

#### エラー応答
エラー内容 : APIキー未指定及びAPIキーエラー。</br>
ステータスコード : `403 Forbidden`</br>
コンテンツ :
```json
{
    "message": "Forbidden"
}
```
</br>

エラー内容 : リクエストデータが不正(画像IDが不存在 or 画像ID未指定)。</br>
ステータスコード : `400 BAD REQUEST`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "ID is not exist in table! ID:{ID}"
}
```

エラー内容 : サーバエラー。</br>
ステータスコード : `500 INTERNAL SERVER ERROR`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "エラー内容"
}
```

<p align="right">(<a href="#top">トップへ</a>)</p>

---


### 5.画像情報更新
画像IDのEpaper画像フォーマット変換可能状態を更新する。</br></br>
URL : `/image/{id}`</br>
メソッド : `PATCH`</br>
httpヘッダー :
```text
Content-Type: application/json
x-api-key: "APIキー"
```

リクエストデータ :
```json
{
    "convertible": Epaper画像フォーマット変換可能状態(undetermined: 未判定, enabled: 変換可能, invalid: 変換不可)
}
```

#### 正常応答
HTTPステータスコード : `200 OK`</br>
コンテンツ :
```json
{
    "result": "OK"
}
```

#### エラー応答
エラー内容 : APIキー未指定及びAPIキーエラー。</br>
ステータスコード : `403 Forbidden`</br>
コンテンツ :
```json
{
    "message": "Forbidden"
}
```
</br>

エラー内容 : リクエストデータが不正(画像IDが不存在 or 画像ID未指定)。</br>
ステータスコード : `400 BAD REQUEST`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "ID is not exist in table! ID:{ID}"
}
```

エラー内容 : サーバエラー。</br>
ステータスコード : `500 INTERNAL SERVER ERROR`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "エラー内容"
}
```

<p align="right">(<a href="#top">トップへ</a>)</p>

### 6.テーブル更新要求※デバッグ用API
DBを強制的に更新する。</br>
URL : `/update_table`</br>
メソッド : `GET`</br>
httpヘッダー :
```text
x-api-key: "APIキー"
```
リクエストデータ : なし

#### 正常応答
HTTPステータスコード : `200 OK`</br>
コンテンツ :
```json
{
    "result": "OK"
}
```

#### エラー応答
エラー内容 : APIキー未指定及びAPIキーエラー。</br>
ステータスコード : `403 Forbidden`</br>
コンテンツ :
```json
{
    "message": "Forbidden"
}
```
</br>

エラー内容 : サーバエラー。</br>
ステータスコード : `500 INTERNAL SERVER ERROR`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "エラー内容"
}
```

<p align="right">(<a href="#top">トップへ</a>)</p>

### 7.画像削除
画像IDの単体及び複数削除。</br></br>
URL : `/deletes`</br>
メソッド : `DELETE`</br>
httpヘッダー :
```text
Content-Type: application/json
x-api-key: "APIキー"
```

リクエストデータ :
```json
{
    "ids": ["ID", ...]
}
```

#### 正常応答
HTTPステータスコード : `200 OK`</br>
コンテンツ :
```json
{
    "result": ["OK", ...]
}
```

#### エラー応答
エラー内容 : APIキー未指定及びAPIキーエラー。</br>
ステータスコード : `403 Forbidden`</br>
コンテンツ :
```json
{
    "message": "Forbidden"
}
```
</br>

エラー内容 : リクエストデータが不正(画像IDが不存在 or 画像ID未指定)。</br>
ステータスコード : `400 BAD REQUEST`</br>
コンテンツ :
```json
{
    "result": ["NG", ...],
    "result_detail": "ID is not exist in table!"
}
```

エラー内容 : サーバエラー。</br>
ステータスコード : `500 INTERNAL SERVER ERROR`</br>
コンテンツ :
```json
{
    "result": "NG",
    "result_detail": "エラー内容"
}
```

---


## トラブルシューティング
### 各種設定を変更したい
src\samconfig.toml ファイルを編集する。</br>

#### スタック名の変更
```src\samconfig.toml:toml
[default.deploy.parameters]
stack_name = "(スタック名を指定)"
(略)
```

#### その他のパラメータ
```src\samconfig.toml:toml
[default.deploy.parameters]
(略)
parameter_overrides="StageName=(デプロイするステージ名) AwsS3Bucket=(画像アップロード/ダウンロード先S3バケット名) ApiKeyName=(APIキー名) ImageMngDbTableName=(画像IDとURL管理DynamoDBテーブル名) LogLevel=(ログ出力レベル(0以下または数値以外:出力しない))"
```
※ルートフォルダでコマンドラインを起動し、Python仮想環境を起動した上で下記のコマンドを実行することでも設定の変更が行える。
```dos
cd src
sam deploy --guided
```
※設定を変更しない場合は、項目自体を削除する。</br>
　ex:ログ出力レベルの設定だけを変更したい場合
```src\samconfig.toml:toml
[default.deploy.parameters]
(略)
parameter_overrides="LogLevel=(ログ出力レベル(0以下または数値以外:出力しない))"
```
各種設定項目は下記のとおりである。</br>
| 項目名 | 設定内容 | デフォルト値 |
| :--- | :--- | :--- |
| StageName | ステージ名 | dev |
| AwsS3Bucket | 画像アップロード/ダウンロード先S3バケット名 | 5.65-epaper-app-serever-assets |
| ApiKeyName | APIキー名 | RestApiKey |
| ImageMngDbTableName | 画像IDとURL管理DynamoDBテーブル名 | Image-ID-URL-mng |
| LogLevel | ログ出力レベル</br>(0以下または数値以外:出力しない) | 10 |

### デプロイに失敗する
- srcフォルダ以下に余分なファイルが存在していないか確認し、存在していた場合は余分なファイルを削除してからデプロイを実行する。</br>
- しばらく時間をおいてからデプロイを行う。</br>
時間をおいてもデプロイに失敗する場合、[【参考】デプロイした環境一式を削除したい場合](#3参考デプロイした環境一式を削除したい場合) を参考に、</br>
AWS上の環境一式を削除したうえでデプロイを実行する。</br>
<span style="color: red; ">**※削除を行うとAPIのルートURLが変更される。**</span>

### ローカルで動作確認を行いたい
localstackを使用することでローカルでの動作確認が可能となる。</br>
※Dockerおよびlocalstackをインストールする必要がある。</br>
　また、Python仮想環境に"aws-sam-cli-local"パッケージをインストールする必要があり、</br>
　デプロイ実行前にDockerおよびlocalstackが起動状態にある必要がある。</br>
localstack上でデプロイを行う際は、Python仮想環境起動状態で、ルートフォルダから下記コマンドを実行する。
```dos
cd src
sam build --use-container
samlocal deploy
```

<p align="right">(<a href="#top">トップへ</a>)</p>
