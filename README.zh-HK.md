# TI TMS9918

以 Python 實現的 Texas Instruments TMS9918A、TMS9928A 和 TMS9929A 視像顯示處理器，每次推進一個主時鐘節拍，並以 TI 1982 年的數據手冊為準。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![CI](https://github.com/gufranco/ti-tms9918-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/ti-tms9918-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/ti-tms9918-python)](https://github.com/gufranco/ti-tms9918-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**348** 個不同的 SG-1000 映像檔各啟動 **600** 幀，其中 **203** 個零售版映像檔的屬性失敗為 **0**，在手冊中找到 **64** 處引文，**3** 款晶片，**766** 個測試，**100%** 語句和分支覆蓋率，沒有依賴套件

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

晶片上電時暫存器和視像記憶體的內容是亂的，所以範例先將它重設，並讀取一次狀態以清除地址鎖存器。五次暫存器寫入以 Graphics I 開啟顯示，背景色為深藍色。三次數據寫入經由埠進行，每次都在處理器的下一個存取窗口寫入視像記憶體。第一行的第一格是圖案 1，其最上一列以一個白色點開始。

## 安裝

| 要求   | 版本                     |
| :----- | :----------------------- |
| Python | 3.12 或更新              |
| git    | 任何版本，用於取得子模組 |

```bash
git clone --recurse-submodules https://github.com/gufranco/ti-tms9918-python.git
cd ti-tms9918-python
python3 tms9918/doctor.py
```

套件只匯入標準程式庫。子模組是 `zilog-z80-python`，只有普查會使用它。從下載 zip 連結取得的原始碼封存檔沒有子模組：此時普查及其測試會報告無法執行的原因，其他一切正常運作。

診斷腳本檢查機器和簽出的程式碼，最後輸出一行結果。提交錯誤報告時，請貼上它的完整輸出。

```
  10 checks, nothing to report
```

版本發佈遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根據提交歷史產生。每個版本都會加上標籤，並列在[版本發佈頁面](https://github.com/gufranco/ti-tms9918-python/releases)上。

## 介面

`tms9918.Chip(model, memory=None, seed=UNSET_SEED)` 建立一款晶片。`model` 為必填。`memory` 是任何具有 `read8(address)` 和 `write8(address, value)` 的物件，省略時晶片會建立一個內容為亂數的 16 KB `Vram`。`seed` 設定暫存器和該 `Vram` 的上電亂數。

| 型號       | 別名    | 行數 | 幀率     | 視像輸出           | CPUCLK 和 GROMCLK 針腳 |
| :--------- | :------ | :--- | :------- | :----------------- | :--------------------- |
| `tms9918a` | `9918a` | 262  | 約 60 Hz | 複合視像           | 有                     |
| `tms9928a` | `9928a` | 262  | 約 60 Hz | 亮度及兩個色差訊號 | 沒有                   |
| `tms9929a` | `9929a` | 313  | 約 50 Hz | 亮度及兩個色差訊號 | 沒有                   |

### 呼叫

| 呼叫                   | 作用                                                                                            |
| :--------------------- | :---------------------------------------------------------------------------------------------- |
| `reset()`              | 等同 RESET 針腳的作用：清除暫存器 0 和 1 以及三個狀態旗標，並將電子束移到頂部消隱區。返回該晶片 |
| `write_control(value)` | 向控制埠寫入一個位元組：視像記憶體地址的一半，或暫存器寫入的一半                                |
| `write_data(value)`    | 向視像記憶體寫入一個位元組。它在下一個存取窗口寫入                                              |
| `read_data()`          | 返回讀取緩衝區，然後在下一個存取窗口取得下一個位元組                                            |
| `read_status()`        | 返回狀態位元組，並清除 F、5S 和 C 旗標                                                          |
| `tick()`               | 一個主時鐘週期。在 TMS9918A 上返回 `CPUCLK` 和 `GROMCLK` 的邊沿，在其他晶片上返回 0             |
| `clock()`              | 一個點，即兩個節拍                                                                              |
| `run_dots(count)`      | `count` 個點                                                                                    |

### 狀態

| 屬性        | 含義                                                                                                                       |
| :---------- | :------------------------------------------------------------------------------------------------------------------------- |
| `line`      | 行號，從第一個有效顯示行起計                                                                                               |
| `dot`       | 點號，從圖案模式有效顯示區的第一個點起計                                                                                   |
| `region`    | 最後一個點所在的 `active`、`border`、`blanking`、`sync` 或 `burst`                                                         |
| `colour`    | 最後一個點的顏色索引 0 至 15；外部視像透出之處為 `EXTERNAL`；沒有繪製任何內容之處為 `None`。透明背景色顯示為黑色，即顏色 1 |
| `interrupt` | INT 針腳被觸發期間為 True                                                                                                  |
| `status`    | 狀態位元組，讀取時不清除任何內容                                                                                           |
| `registers` | 八個唯寫暫存器，以 `bytearray` 表示                                                                                        |
| `mode`      | 暫存器所選擇的顯示模式，例如 `graphics1`、`graphics2`、`multicolor`、`text`，或 `text+graphics2` 之類的組合                |
| `model`     | 標準型號名稱                                                                                                               |
| `part`      | `Model` 記錄：`lines`、`output`、`clock_pins`、`aliases`、`summary`                                                        |
| `memory`    | 視像記憶體物件                                                                                                             |
| `cycles`    | 自晶片建立以來的主時鐘節拍數                                                                                               |

### 模組內容

| 名稱                                                      | 內容                                                                                                                                                               |
| :-------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tms9918.MODELS`                                          | 三個 `Model` 記錄，以標準名稱為鍵                                                                                                                                  |
| `tms9918.Vram(fill=None, seed=UNSET_SEED)`                | 16 KB 視像記憶體。`fill` 是一個位元組值或一個位元組串，沒有它時內容由 `seed` 產生亂數                                                                              |
| `tms9918.UnknownModelError`                               | 型號名稱缺失或未知時拋出。訊息會列出可接受的名稱                                                                                                                   |
| `tms9918.CPUCLK`、`tms9918.GROMCLK`                       | `tick()` 返回值中標示各時鐘針腳脈衝的位元。CPUCLK 每 3 個節拍產生一次脈衝，GROMCLK 每 24 個節拍一次                                                                |
| `tms9918.EXTERNAL`                                        | 外部視像透出之處的 `colour` 值                                                                                                                                     |
| `tms9918.COMPOSITE`、`tms9918.DIFFERENCE`                 | Table 2-3 為每種顏色列出的訊號電平                                                                                                                                 |
| `tms9918.COMPOSITE_SPECIAL`、`tms9918.DIFFERENCE_SPECIAL` | Table 2-3 為黑電平、同步、色同步訊號和外部視像列出的電平。`COMPOSITE_SPECIAL` 含 `black`、`burst` 和 `sync`，`DIFFERENCE_SPECIAL` 含 `black`、`sync` 和 `external` |
| `tms9918.burst(model)`                                    | `tms9928a` 或 `tms9929a` 兩路色差輸出上的色同步訊號                                                                                                                |
| `tms9918.__version__`                                     | 已安裝的版本                                                                                                                                                       |

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

`COMPOSITE` 將每個顏色索引對應到其亮度和色度電平，表中沒有列出色度之處為 `None`。`DIFFERENCE` 將每個顏色索引對應到其亮度和兩個色差電平。兩者都按 Table 2-3 的原樣抄錄。

### 各型號的幀長度

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

所有晶片的每一行都是 342 個點。重設後的第一個完整幀，從一個 F 旗標計到下一個。

## 精靈與狀態位元組

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

五個精靈位於同一行，即第 50 行。晶片繪製其中四個，設定 5S 旗標並在低位元記錄第五個精靈的平面編號 4，又因為繪製出的四個精靈互相重疊而設定重合旗標。

## 處理器的存取窗口

處理器只能在窗口內存取視像記憶體：在有精靈的 Graphics I 和 II 中每 16 個記憶體週期一次，在 Text 模式中每 3 個一次，在 Multicolor 中每 4 個一次，任何存取的等待時間都不超過約 8 微秒。手冊沒有說明每個窗口落在哪一個點上。本套件從 openMSX 的 MSX1 表格取得窗口位置，並以 TI 列出的每個界限對其進行測試。

openMSX 記錄了在真實 MSX1 上的一項量度：相隔 26 個或更少處理器週期的數據寫入會損壞視像記憶體，相隔 27 個或更多則永遠不會。模型重現了這兩方面。若第二次存取在第一次仍在等待時到達，便會取代第一次，所以上面的範例讓每次寫入在下一次之前完成。

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

在 Graphics I 幀的有效顯示期間，向 TMS9929A 寫入三個位元組。相隔 12 個點時，第二個位元組在第一個找到窗口之前到達，所以第一個位元組遺失，而地址已經前移。相隔 41 個點時，即多於時鐘為主時鐘三分之一的處理器的 27 個週期，每個位元組都能寫入。

## 普查

```bash
python3 -m conformance.census /path/to/sg1000/library --frames 600 --jobs 10
```

普查在一塊 SG-1000 主機板上，配合 `zilog-z80-python` 處理器，啟動 SG-1000 映像檔庫中的每個映像檔，並讓每個映像檔執行固定數量的幀。它接受目錄、zip 封存檔和單個映像檔，並按摘要值將每個不同的映像檔只計算一次。它會列印摘要，寫入 [`conformance/corpus.json`](conformance/corpus.json)，並在任何屬性失敗時以 1 退出。

部分卡帶自帶 RAM，其中包括 Othello、The Castle 和台灣的 Dahjee 主機板。[`conformance/boards.json`](conformance/boards.json) 按照 MAME 的 SG-1000 軟件清單的記錄，以整個檔案的 SHA-1 標示每個此類映像檔及其主機板，測試框架會將 RAM 對應到該主機板放置它的位置。其他所有映像檔都在普通主機板上執行。

兩項屬性作為本次執行的關卡檢查：模型在任何映像檔上都不拋出例外，以及每個零售版映像檔都會開啟顯示。在上一次存取完成之前請求的存取會按映像檔計數並列出名稱，但不作關卡檢查，因為已發售的遊戲確實會以快於窗口所允許的速度寫入，而晶片同樣會遺失這些寫入。改版、自製軟件、翻譯版、測試版、SC-3000 程式、`.sf` 和 `.sms` 映像檔以及 BIOS 映像檔永遠不作關卡檢查。

| 上次執行的結果                                                            | 數量               |
| :------------------------------------------------------------------------ | :----------------- |
| 不同的映像檔                                                              | 348                |
| Graphics II                                                               | 279                |
| Graphics I                                                                | 47                 |
| 設定了 Graphics II 位元的 Text                                            | 4                  |
| Multicolor                                                                | 2                  |
| Text                                                                      | 1                  |
| 從未開啟顯示，其中沒有零售版                                              | 25                 |
| 精靈 16 乘 16，未放大                                                     | 261                |
| 精靈 8 乘 8                                                               | 66                 |
| 精靈 16 乘 16，已放大                                                     | 4                  |
| 零售版映像檔上遺失的存取，全部來自 Champion Golf、Golgo 13 和 Sega-Galaga | 7 個映像檔共 47 次 |
| 其餘映像檔上遺失的存取，幾乎全部來自兩款自製軟件                          | 12,629             |

[`conformance/corpus.json`](conformance/corpus.json) 只保存這些數字，不包含任何卡帶的內容，所以測試套件在沒有映像檔庫的機器上也能檢查它們。

## 是否正確

TI 列出的每個測試可觸及的事實，都以程式碼加以核對。[`conformance/hardware.json`](conformance/hardware.json) 記載每個事實及其原句和頁碼，[`conformance/hardware.test.py`](conformance/hardware.test.py) 和 [`conformance/display.test.py`](conformance/display.test.py) 依據它們驅動晶片模型。`python3 -m conformance.quotes` 會在手冊中找出每一句引文。

手冊沒有列出的每個數值都放在同一檔案的 `notStated` 下，標示為未經核實，並附有來源及能確定它的量度方法。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出了這些數值。手冊自相矛盾之處記錄在 [`conformance/divergences.json`](conformance/divergences.json)。

## 參與開發

| 需要                                 | 位置                                                                  |
| :----------------------------------- | :-------------------------------------------------------------------- |
| 每項關卡檢查及其執行次序             | [CONTRIBUTING.md](CONTRIBUTING.md)                                    |
| 供程式編寫代理使用的相同資料         | [AGENTS.md](AGENTS.md)                                                |
| 本儲存庫與同系列其他儲存庫共用的標準 | [FAMILY.md](FAMILY.md)                                                |
| 錯誤報告                             | [GitHub Issues](https://github.com/gufranco/ti-tms9918-python/issues) |
| 安全報告                             | [SECURITY.md](SECURITY.md)                                            |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 tms9918/core.test.py
```

每個模組旁邊都有一個以其命名的測試檔案，每個都可以如上所示獨立執行。覆蓋率是硬性關卡檢查，要求 100% 語句和分支覆蓋率。

## 參考資料

- _TMS9918A/TMS9928A/TMS9929A Video Display Processors Data Manual_，Texas Instruments，1982 年 11 月。105 頁，6,785,534 位元組，SHA-256 `3991f0c691b83036bbb96d8e60e8d4ed4cfbb5eed9567ad61737570771113450`。它不可再分發，也不在本儲存庫中。`python3 -m conformance.documents` 從 https://bitsavers.org/components/ti/TMS9900/TMS9918A_TMS9928A_TMS9929A_Video_Display_Processors_Data_Manual_Nov82.pdf 下載它，並拒絕任何其他檔案。
- _TMS 9929A European Line Format Video Display Processor, Preliminary Data_，Texas Instruments，1980 年 3 月 24 日。20 頁，7,934,967 位元組，SHA-256 `5d80fd454a3c5e5d1fe700ec6bb76ee3f70048577ffdc7da6833394b6f41bc9e`。其第 10 頁是表 2-3 的較早版本，確定了色同步電平的小數點。它不在本儲存庫中。`python3 -m conformance.documents` 從 https://archive.org/download/tms-9929-a/TMS9929A.pdf 下載它，並拒絕任何其他檔案。
- openMSX，`src/video/VDPAccessSlots.cc` 和 `src/video/VDP.hh`，提交 `99c28389d775b945c57be27df1def0925e28abd8`，https://github.com/openMSX/openMSX ，用於存取窗口位置。只取事實，沒有採用任何程式碼。
- MAME，`src/devices/video/tms9928a.cpp`，提交 `dc00cf3517eef30587b33efbf1e1c63ad3531b58`，https://github.com/mamedev/mame ，用於手冊和 openMSX 都沒有涵蓋的行為；以及同一提交的 `hash/sg1000.xml`，用於卡帶主機板。只取事實，沒有採用任何程式碼。

## 引用本專案

[CITATION.cff](CITATION.cff) 在每次版本發佈時，由標記套件版本的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。
