# E-Paper-App-Server-for-5.65
5.65Epaper向けアプリサーバAPIソース

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
││└(※app.pyが参照する自作モジュール格納フォルダ)
│├app.py
│├requirements.txt
│├samconfig.toml
│└template.yaml
├uml
│├sequence
││└ESL_sequence.pu ※シーケンス図
│└usecase
│  └ESL_usecase.pu ※ユースケース図
└README.md ※このファイル
</pre>

<p align="right">(<a href="#top">トップへ</a>)</p>

## 環境構築～AWSデプロイ
※AWSデプロイを行う際は環境構築を先に行う必要がある。</br>
　また、コマンドライン記述の"*.venv*"の箇所は任意のフォルダ名で可。

### 1.環境構築

ルートフォルダでコマンドラインを起動し、下記コマンドを入力する。
```dos
py -m venv .venv
.venv\Scripts\activate.bat
py -m pip install -r src\requirements.txt
```

<p align="right">(<a href="#top">トップへ</a>)</p>

---


### 2.AWSデプロイ
#### 認証情報の設定
下記の手順で認証情報の設定を行う</br>
※AWSアカウントおよびIAMユーザは作成済みであることを前提とする。
1. [IAM ユーザーの認証情報(アクセスキーID・シークレットアクセスキー)を発行する](https://docs.aws.amazon.com/ja_jp/IAM/latest/UserGuide/id_credentials_access-keys.html)
1. [AWS CLI をインストールする](https://docs.aws.amazon.com/ja_jp/cli/latest/userguide/cli-configure-files.html)
1. [AWS CLI に IAM ユーザーの認証情報を設定する](https://docs.aws.amazon.com/ja_jp/cli/latest/userguide/cli-configure-files.html)

#### デプロイ手順
※(python仮想環境を立ち上げていない場合、)ルートフォルダでコマンドラインを起動し、下記コマンドでpython仮想環境を起動する。
```dos
.venv\Scripts\activate.bat
```

1.python仮想環境起動状態で、ルートフォルダから下記コマンドを実行する。
```dos
bat\_aws_sam_deploy.bat
```

2.実行完了後にコマンドラインに下記のような表示がされ、</br>
<span style="color: red; ">Value</span>に表示されているURLがAPIのルートURLとなる。
```
(略)
CloudFormation outputs from deployed stack
---------------------------------------------------------------------------------------------------------------------
Outputs
---------------------------------------------------------------------------------------------------------------------
Key                 FunctionUrl
Description         -
Value               https://***.lambda-url.(リージョン).on.aws/
---------------------------------------------------------------------------------------------------------------------
Successfully created/updated stack - Epaper-apl-server-apim in (リージョン)
```

<p align="right">(<a href="#top">トップへ</a>)</p>

---


### 3.【参考】デプロイした環境一式を削除したい場合
※(python仮想環境を立ち上げていない場合、)ルートフォルダでコマンドラインを起動し、下記コマンドでpython仮想環境を起動する。
```dos
.venv\Scripts\activate.bat
```

python仮想環境起動状態で、ルートフォルダから下記コマンドを実行する。
```dos
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


### 2.テーブル更新要求
サーバ内のhash-table更新を要求する。</br></br>
URL : `/update_table`</br>
メソッド : `GET`</br>
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


### 3.画像リスト要求

「画像IDと画像URL」のリストを取得する。</br></br>
URL : `/images`</br>
メソッド : `GET`</br>
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
        "url": "画像ダウンロード用署名付きURL"
      }
    ]
}
```

#### エラー応答
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

## トラブルシューティング
### 画像アップロード/ダウンロード先S3バケット名を変更したい
src\samconfig.toml ファイルに下記設定を追加する。
```src\samconfig.toml:toml
[default.deploy.parameters]
(略)
parameter_overrides="AwsS3Bucket=(S3バケット名を設定)"
```

### デプロイに失敗する
しばらく時間をおいてからデプロイを行う。</br>
時間をおいてもデプロイに失敗する場合、[【参考】デプロイした環境一式を削除したい場合](#3参考デプロイした環境一式を削除したい場合) を参考に、</br>
AWS状の環境一式を削除したうえでデプロイを行う。</br>
<span style="color: red; ">**※削除を行うとAPIのルートURLが変更される。**</span>

### ローカルで動作確認を行いたい
localstackを使用することでローカルでの動作確認が可能となる。</br>
※Dockerおよびlocalstackをインストールする必要がある。</br>
　また、python仮想環境に"aws-sam-cli-local"パッケージをインストールする必要があり、</br>
　デプロイ実行前にDockerおよびlocalstackが起動状態にある必要がある。</br>
localstack上でデプロイを行う際は、python仮想環境起動状態で、ルートフォルダから下記コマンドを実行する。
```dos
sam build
samlocal deploy
```

<p align="right">(<a href="#top">トップへ</a>)</p>
