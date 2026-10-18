# TI TMS9918

Texas InstrumentsのTMS9918A、TMS9928A、TMS9929AビデオディスプレイプロセッサをPythonで実装したものです。マスタークロックを1ティックずつ進め、TIの1982年のデータマニュアルに準拠させています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/ti-tms9918-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/ti-tms9918-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/ti-tms9918-python)](https://github.com/gufranco/ti-tms9918-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

異なるSG-1000イメージ**348**本をそれぞれ**600**フレーム起動、市販の**203**本で性質の不合格**0**件、マニュアル内で所在を確認した引用**64**件、**3**品種、テスト**719**件、ステートメントとブランチのカバレッジ**100%**、依存関係なし

```python
import tms9918

part = tms9918.Chip("tms9918a")
part.reset()
part.read_status()

for register, value in {1: 0x40, 2: 0x06, 3: 0x80, 4: 0x00, 7: 0x04}.items():
    part.write_control(value)
    part.write_control(0x80 | register)

for address, value in {0x1800: 0x01, 0x0008: 0x80, 0x2000: 0xF0}.items():
    part.write_control(address & 0xFF)
    part.write_control(0x40 | address >> 8)
    part.write_data(value)
    part.run_dots(16)

while (part.line, part.dot) != (0, 0):
    part.clock()

shown = []
for _ in range(3):
    part.clock()
    shown.append((part.region, part.colour))
print(shown)
print(part.model, part.line, part.dot)
```

```
[('active', 15), ('active', 4), ('active', 4)]
tms9918a 0 3
```

チップは電源投入時にレジスタとビデオメモリが不定の値になっているため、この例ではリセットしたあとステータスを1回読み出してアドレスラッチをクリアしています。5回のレジスタ書き込みで、Graphics Iモード、濃い青の背景色で表示をオンにします。3回のデータ書き込みはポートを通り、それぞれプロセッサの次のアクセスウィンドウでビデオメモリに書き込まれます。最初のラインの最初のセルはパターン1で、その最上段は白いドット1つから始まります。

## インストール

| 要件 | バージョン |
|:--|:--|
| Python | 3.12以降 |
| git | 任意。サブモジュールの取得に使います |

```bash
git clone --recurse-submodules https://github.com/gufranco/ti-tms9918-python.git
cd ti-tms9918-python
python3 tms9918/doctor.py
```

パッケージは標準ライブラリ以外を何もインポートしません。サブモジュールは`zilog-z80-python`で、使うのは全数調査だけです。ZIPダウンロードのリンクから得たソースアーカイブにはサブモジュールが含まれません。その場合、全数調査とそのテストは実行できない理由を報告し、それ以外はすべて動作します。

ドクターはマシンとチェックアウトを検査し、最後に1行を出力します。バグ報告には、その出力全体を貼り付けてください。

```
  10 checks, nothing to report
```

リリースは[Semantic Versioning](https://semver.org/)に従い、semantic-releaseがコミット履歴から作成します。すべてのリリースにはタグが付けられ、[リリースページ](https://github.com/gufranco/ti-tms9918-python/releases)に掲載されます。

## インターフェース

`tms9918.Chip(model, memory=None, seed=UNSET_SEED)`はチップを1つ構築します。`model`は必須です。`memory`は`read8(address)`と`write8(address, value)`を持つ任意のオブジェクトで、省略するとチップは不定の値で埋めた16 KBの`Vram`を構築します。`seed`は、レジスタとその`Vram`の電源投入時の不定値を決めます。

| モデル | 別名 | ライン数 | フレームレート | ビデオ出力 | CPUCLKとGROMCLKのピン |
|:--|:--|:--|:--|:--|:--|
| `tms9918a` | `9918a` | 262 | 約60 Hz | コンポジット | あり |
| `tms9928a` | `9928a` | 262 | 約60 Hz | 輝度と2つの色差信号 | なし |
| `tms9929a` | `9929a` | 313 | 約50 Hz | 輝度と2つの色差信号 | なし |

### 呼び出し

| 呼び出し | 効果 |
|:--|:--|
| `reset()` | RESETピンと同じ動作です。レジスタ0と1、および3つのステータスフラグをクリアし、ビームを上部のブランキングに移します。チップを返します |
| `write_control(value)` | コントロールポートへの1バイトです。ビデオメモリのアドレスの半分、またはレジスタ書き込みの半分になります |
| `write_data(value)` | ビデオメモリへの1バイトです。次のアクセスウィンドウで書き込まれます |
| `read_data()` | リードバッファを返し、次のアクセスウィンドウで次のバイトを取得します |
| `read_status()` | ステータスバイトを返し、F、5S、Cの各フラグをクリアします |
| `tick()` | マスタークロック1周期です。TMS9918Aでは`CPUCLK`と`GROMCLK`のエッジを返し、ほかの品種では0を返します |
| `clock()` | 1ドット、つまり2ティックです |
| `run_dots(count)` | `count`ドットです |

### 状態

| 属性 | 意味 |
|:--|:--|
| `line` | ライン番号です。最初のアクティブラインから数えます |
| `dot` | ドット番号です。パターンモードのアクティブ領域の最初のドットから数えます |
| `region` | 直前のドットの`active`、`border`、`blanking`、`sync`、`burst`のいずれかです |
| `colour` | 直前のドットの色番号0から15です。外部ビデオが透けて見える箇所では`EXTERNAL`、何も描画されない箇所では`None`です。透明な背景色は黒、つまり色1として表示されます |
| `interrupt` | INTピンがアサートされている間Trueです |
| `status` | ステータスバイトです。何もクリアせずに読み出します |
| `registers` | 8個の書き込み専用レジスタを`bytearray`で表したものです |
| `mode` | レジスタが選択する表示モードです。`graphics1`、`graphics2`、`multicolor`、`text`、または`text+graphics2`のような組み合わせです |
| `model` | 正規のモデル名です |
| `part` | `Model`レコードです。`lines`、`output`、`clock_pins`、`aliases`、`summary`を持ちます |
| `memory` | ビデオメモリのオブジェクトです |
| `cycles` | チップの構築以降のマスタークロックのティック数です |

### モジュールの内容

| 名前 | 内容 |
|:--|:--|
| `tms9918.MODELS` | 3つの`Model`レコードです。正規名をキーとします |
| `tms9918.Vram(fill=None, seed=UNSET_SEED)` | 16 KBのビデオメモリです。`fill`はバイト値またはバイト列で、省略すると内容は`seed`から不定の値で埋められます |
| `tms9918.UnknownModelError` | モデル名がない場合や未知の場合に送出されます。メッセージには受け付ける名前が列挙されます |
| `tms9918.CPUCLK`, `tms9918.GROMCLK` | `tick()`の戻り値のうち、各クロックピンのパルスを示すビットです。CPUCLKは3ティックごと、GROMCLKは24ティックごとにパルスを出します |
| `tms9918.EXTERNAL` | 外部ビデオが透けて見える箇所の`colour`の値です |
| `tms9918.COMPOSITE`, `tms9918.DIFFERENCE` | Table 2-3が各色について記載する信号レベルです |
| `tms9918.COMPOSITE_SPECIAL`, `tms9918.DIFFERENCE_SPECIAL` | Table 2-3が黒、同期、カラーバースト、外部ビデオについて記載するレベルです。`COMPOSITE_SPECIAL`は`black`、`burst`、`sync`を持ち、`DIFFERENCE_SPECIAL`は`black`、`sync`、`external`を持ちます |
| `tms9918.burst(model)` | `tms9928a`または`tms9929a`の2つの色差出力に乗るカラーバーストです |
| `tms9918.__version__` | インストールされているバージョンです |

```python
import tms9918

for name, model in tms9918.MODELS.items():
    print(name, model.aliases, model.lines, model.output, model.clock_pins)

print(tms9918.COMPOSITE[0xF], tms9918.DIFFERENCE[0x4], tms9918.burst("tms9929a"))

try:
    tms9918.Chip("tms9938")
except tms9918.UnknownModelError as error:
    print(error)
```

```
tms9918a ('9918a',) 262 composite True
tms9928a ('9928a',) 262 colour difference False
tms9929a ('9929a',) 313 colour difference False
(1.0, None) (0.4, 0.4, 1.0) (0.0, 0.73, 0.2)
tms9938 is not a model this package covers; it has tms9918a, tms9928a, tms9929a
```

`COMPOSITE`は各色番号を輝度と彩度のレベルに対応付けます。表に彩度の記載がない箇所は`None`です。`DIFFERENCE`は各色番号を輝度と2つの色差レベルに対応付けます。どちらもTable 2-3の記載どおりに写したものです。

### モデルごとのフレーム長

```python
import tms9918


def frame(part):
    part.read_status()
    dots = 0
    while not part.status & 0x80:
        part.clock()
        dots += 1
    return dots


for name in ("tms9918a", "tms9928a", "tms9929a"):
    part = tms9918.Chip(name)
    part.reset()
    frame(part)
    print(part.model, frame(part), frame(part) // 342, part.part.clock_pins)

print(tms9918.Chip("9929a").model)
```

```
tms9918a 89604 262 True
tms9928a 89604 262 False
tms9929a 107046 313 False
tms9929a
```

フレームは、どの品種でも1ラインあたり342ドットです。リセット後の最初の完全なフレームは、あるFフラグから次のFフラグまでで数えます。

## スプライトとステータスバイト

```python
import tms9918
from tms9918.memory import Vram

part = tms9918.Chip("tms9928a", Vram(fill=0))
part.reset()
part.read_status()
for register, value in {1: 0x40, 5: 0x36, 6: 0x07}.items():
    part.write_control(value)
    part.write_control(0x80 | register)

for plane in range(5):
    entry = 0x1B00 + plane * 4
    part.memory.write8(entry, 49)
    part.memory.write8(entry + 1, plane * 6)
    part.memory.write8(entry + 3, 0x0F)
part.memory.write8(0x1B00 + 5 * 4, 0xD0)
part.memory.write8(0x3800, 0xFF)

while (part.line, part.dot) != (51, 0):
    part.clock()

status = part.read_status()
print(f"5S {bool(status & 0x40)}, fifth plane {status & 0x1F}, coincidence {bool(status & 0x20)}")
```

```
5S True, fifth plane 4, coincidence True
```

5つのスプライトがライン50を共有しています。チップは4つを描画し、5Sフラグを立てて、5番目のスプライトのプレーン番号である4を下位ビットに入れます。さらに、描画された4つのスプライトが重なっているため、衝突フラグを立てます。

## プロセッサのアクセスウィンドウ

プロセッサがビデオメモリにアクセスできるのはウィンドウの間だけです。スプライトありのGraphics IとIIでは16メモリサイクルに1回、Textモードでは3サイクルに1回、Multicolorでは4サイクルに1回で、どのアクセスも約8マイクロ秒より長くは待ちません。各ウィンドウがどのドットに来るかは、マニュアルには書かれていません。このパッケージはその位置をopenMSXのMSX1用テーブルから取り、TIが記載したすべての上限値をそれに対してテストしています。

openMSXは実機のMSX1での測定結果を記録しています。データ書き込みの間隔が26プロセッササイクル以下だとビデオメモリが破損し、27以上では決して破損しません。このモデルはその両方を再現します。最初のアクセスがまだ待っている間に2番目のアクセスが来ると、2番目が最初のものを置き換えます。そのため、上の例ではそれぞれの書き込みが次の書き込みの前に完了するようにしています。

```python
import tms9918
from tms9918.memory import Vram


def burst(gap):
    part = tms9918.Chip("tms9929a", Vram(fill=0))
    part.reset()
    part.read_status()
    part.write_control(0x40)
    part.write_control(0x81)
    while (part.line, part.dot) != (10, 0):
        part.clock()
    part.write_control(0x00)
    part.write_control(0x40)
    for value in (0x11, 0x22, 0x33):
        part.write_data(value)
        part.run_dots(gap)
    part.run_dots(400)
    return [hex(part.memory.read8(address)) for address in range(3)]


print(burst(12))
print(burst(41))
```

```
['0x0', '0x22', '0x33']
['0x11', '0x22', '0x33']
```

Graphics Iのフレームのアクティブ表示中に、TMS9929Aへ3バイトを送ります。12ドット間隔では、1バイト目がウィンドウを得る前に2バイト目が届くため、1バイト目は失われ、アドレスはすでに先へ進んでいます。41ドット間隔は、マスタークロックの3分の1で動くプロセッサの27サイクルより長く、すべてのバイトが書き込まれます。

## 全数調査

```bash
python3 -m conformance.census /path/to/sg1000/library --frames 600 --jobs 10
```

全数調査は、SG-1000ライブラリ内のすべてのイメージを、`zilog-z80-python`プロセッサを載せたSG-1000ボード上で起動し、それぞれを決まったフレーム数だけ実行します。ディレクトリ、ZIPアーカイブ、単体のイメージを受け付け、異なるイメージをダイジェストで1回ずつ数えます。概要を出力し、[`conformance/corpus.json`](conformance/corpus.json)を書き出し、性質が破れた場合は終了コード1で終了します。

一部のカートリッジは独自のRAMを搭載しています。Othello、The Castle、台湾のDahjeeボードなどです。[`conformance/boards.json`](conformance/boards.json)は、MAMEのSG-1000ソフトウェアリストの記録に従い、それらのイメージをファイル全体のSHA-1とボードの組で列挙しています。ハーネスは、そのボードがRAMを置く位置にRAMをマップします。それ以外のイメージはすべて素のボードで実行します。

実行のゲートになる性質は2つです。どのイメージでもモデルが例外を送出しないこと、そしてすべての市販イメージが表示をオンにすることです。前のアクセスが処理される前に要求されたアクセスは、イメージごとに数えて名前を挙げますが、ゲートにはしません。発売済みのゲームは実際にウィンドウが許すより速く書き込み、チップもそれらの書き込みを失うからです。改造版、自作ソフト、翻訳版、ベータ版、SC-3000のプログラム、`.sf`と`.sms`のイメージ、BIOSイメージはゲートになりません。

| 直近の実行の結果 | 件数 |
|:--|:--|
| 異なるイメージ | 348 |
| Graphics II | 279 |
| Graphics I | 47 |
| Graphics IIのビットが立ったText | 4 |
| Multicolor | 2 |
| Text | 1 |
| 表示をオンにしなかったもの。市販品は含まれません | 25 |
| 16×16のスプライト、拡大なし | 261 |
| 8×8のスプライト | 66 |
| 16×16のスプライト、拡大あり | 4 |
| 市販イメージで失われたアクセス。すべてChampion Golf、Golgo 13、Sega-Galagaのものです | 7イメージで47 |
| それ以外で失われたアクセス。ほぼすべてが2本の自作ソフトによるものです | 12,629 |

[`conformance/corpus.json`](conformance/corpus.json)はそれらの件数だけを保持し、カートリッジ由来のデータは何も含みません。そのため、ライブラリのないマシンでもテストスイートで件数を検証できます。

## 正しいかどうか

TIが記載した事実のうち、テストで到達できるものはすべてコードと照合しています。[`conformance/hardware.json`](conformance/hardware.json)は各事実をその文とページとともに保持し、[`conformance/hardware.test.py`](conformance/hardware.test.py)と[`conformance/display.test.py`](conformance/display.test.py)がそれらに照らしてパーツを動かします。`python3 -m conformance.quotes`は、引用した文のすべてをマニュアル内で見つけます。

マニュアルに記載のない値はすべて、同じファイルの`notStated`の下に未検証として置かれ、その出典と、決着をつけるための測定が添えられています。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)にその一覧があります。マニュアルが自己矛盾している箇所は[`conformance/divergences.json`](conformance/divergences.json)にあります。

## 開発に参加する

| 必要なもの | 場所 |
|:--|:--|
| すべてのゲートと実行順序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| コーディングエージェント向けの同じ内容 | [AGENTS.md](AGENTS.md) |
| このリポジトリがファミリーのほかのリポジトリと共有する標準 | [FAMILY.md](FAMILY.md) |
| バグ報告 | [GitHub Issues](https://github.com/gufranco/ti-tms9918-python/issues) |
| セキュリティ報告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 tms9918/core.test.py
```

各モジュールの隣には、そのモジュール名にちなんだテストファイルがあり、上のようにそれぞれ単独で実行できます。カバレッジはステートメントとブランチの100%を必須とするゲートです。

## 参考文献

- *TMS9918A/TMS9928A/TMS9929A Video Display Processors Data Manual*、Texas Instruments、1982年11月。105ページ、6,785,534バイト、SHA-256 `3991f0c691b83036bbb96d8e60e8d4ed4cfbb5eed9567ad61737570771113450`。再配布はできず、このリポジトリには含まれていません。`python3 -m conformance.documents`がhttps://bitsavers.org/components/ti/TMS9900/TMS9918A_TMS9928A_TMS9929A_Video_Display_Processors_Data_Manual_Nov82.pdf からダウンロードし、それ以外のファイルは拒否します。
- openMSX、コミット`99c28389d775b945c57be27df1def0925e28abd8`時点の`src/video/VDPAccessSlots.cc`と`src/video/VDP.hh`、https://github.com/openMSX/openMSX 。アクセスウィンドウの位置に使用しています。事実のみを利用し、コードは一切取り込んでいません。
- MAME、コミット`dc00cf3517eef30587b33efbf1e1c63ad3531b58`時点の`src/devices/video/tms9928a.cpp`、https://github.com/mamedev/mame 。マニュアルにもopenMSXにもない動作に使用しています。また、同じコミットの`hash/sg1000.xml`をカートリッジのボードに使用しています。事実のみを利用し、コードは一切取り込んでいません。

## 引用

[CITATION.cff](CITATION.cff)は、パッケージのバージョンを刻印するスクリプトによってリリースごとに更新されます。

## ライセンス

MIT。[LICENSE](LICENSE)を参照してください。
