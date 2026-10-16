[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

# TI TMS9918

用 Python 实现的 Texas Instruments TMS9918A、TMS9928A 和 TMS9929A 视频显示处理器，每次推进一个主时钟节拍，并以 TI 1982 年的数据手册为准。

[![CI](https://github.com/gufranco/ti-tms9918-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/ti-tms9918-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/ti-tms9918-python)](https://github.com/gufranco/ti-tms9918-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**348** 个不同的 SG-1000 镜像各启动 **600** 帧，**0** 个属性失败（涵盖其中 **203** 个零售版镜像），在手册中定位到 **62** 处引文，**3** 款芯片，**646** 个测试，**100%** 语句和分支覆盖率，无依赖

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

芯片上电时寄存器和显存的内容是乱的，所以示例先将其复位，再读一次状态以清除地址锁存器。五次寄存器写入以 Graphics I 模式打开显示，背景色为深蓝色。三次数据写入经由端口进行，每一次都在处理器的下一个访问窗口落入显存。第一行的第一个单元格是图案 1，其最上面一行以一个白色点开头。

## 安装

| 要求 | 版本 |
|:--|:--|
| Python | 3.12 或更高 |
| git | 任意版本，用于获取子模块 |

```bash
git clone --recurse-submodules https://github.com/gufranco/ti-tms9918-python.git
cd ti-tms9918-python
python3 tms9918/doctor.py
```

该包不导入标准库以外的任何内容。子模块是 `zilog-z80-python`，只有普查会用到它。通过下载 zip 链接获得的源码归档不含子模块：在那里普查及其测试会报告无法运行的原因，其余一切正常工作。

诊断脚本检查本机和检出的代码，最后输出一行。提交缺陷报告时请粘贴它的完整输出。

```
  10 checks, nothing to report
```

版本发布遵循[语义化版本](https://semver.org/)，由 semantic-release 根据提交历史生成。每个版本都打了标签，并列在[发布页面](https://github.com/gufranco/ti-tms9918-python/releases)上。

## 接口

`tms9918.Chip(model, memory=None, seed=UNSET_SEED)` 构建一颗芯片。`model` 为必填项。`memory` 可以是任何具有 `read8(address)` 和 `write8(address, value)` 的对象，省略时芯片会构建一个内容为乱值的 16 KB `Vram`。`seed` 设置寄存器和该 `Vram` 的上电乱值。

| 型号 | 别名 | 行数 | 帧率 | 视频输出 | CPUCLK 和 GROMCLK 引脚 |
|:--|:--|:--|:--|:--|:--|
| `tms9918a` | `9918a` | 262 | 约 60 Hz | 复合视频 | 有 |
| `tms9928a` | `9928a` | 262 | 约 60 Hz | 亮度和两路色差信号 | 无 |
| `tms9929a` | `9929a` | 313 | 约 50 Hz | 亮度和两路色差信号 | 无 |

### 调用

| 调用 | 作用 |
|:--|:--|
| `reset()` | 与 RESET 引脚的作用相同：清除寄存器 0 和 1 以及三个状态标志，并将电子束移到顶部消隐区。返回该芯片 |
| `write_control(value)` | 向控制端口写一个字节：显存地址的一半，或一次寄存器写入的一半 |
| `write_data(value)` | 向显存写一个字节。它在下一个访问窗口落入 |
| `read_data()` | 返回读缓冲区，然后在下一个访问窗口取下一个字节 |
| `read_status()` | 返回状态字节，并清除 F、5S 和 C 标志 |
| `tick()` | 一个主时钟周期。在 TMS9918A 上返回 `CPUCLK` 和 `GROMCLK` 的边沿，在其他芯片上返回 0 |
| `clock()` | 一个点，即两个节拍 |
| `run_dots(count)` | `count` 个点 |

### 状态

| 属性 | 含义 |
|:--|:--|
| `line` | 行号，从第一个有效显示行开始计数 |
| `dot` | 点号，从图案模式有效显示区的第一个点开始计数 |
| `region` | 最后一个点所在的区域：`active`、`border`、`blanking`、`sync` 或 `burst` |
| `colour` | 最后一个点的颜色索引 0 到 15；外部视频透出处为 `EXTERNAL`，不绘制任何内容处为 `None`。透明背景色显示为黑色，即颜色 1 |
| `interrupt` | INT 引脚有效时为 True |
| `status` | 状态字节，读取时不清除任何内容 |
| `registers` | 八个只写寄存器，类型为 `bytearray` |
| `mode` | 寄存器所选的显示模式，例如 `graphics1`、`graphics2`、`multicolor`、`text`，或 `text+graphics2` 这样的组合 |
| `model` | 规范型号名 |
| `part` | `Model` 记录：`lines`、`output`、`clock_pins`、`aliases`、`summary` |
| `memory` | 显存对象 |
| `cycles` | 自芯片构建以来的主时钟节拍数 |

### 模块内容

| 名称 | 内容 |
|:--|:--|
| `tms9918.MODELS` | 三条 `Model` 记录，以规范名称为键 |
| `tms9918.Vram(fill=None, seed=UNSET_SEED)` | 16 KB 显存。`fill` 是一个字节值或一个字节串，不提供时内容由 `seed` 生成乱值 |
| `tms9918.UnknownModelError` | 型号名缺失或未知时抛出。消息中列出可接受的名称 |
| `tms9918.CPUCLK`、`tms9918.GROMCLK` | `tick()` 返回值中标记各时钟引脚脉冲的位。CPUCLK 每 3 个节拍一个脉冲，GROMCLK 每 24 个节拍一个脉冲 |
| `tms9918.EXTERNAL` | 外部视频透出处的 `colour` 值 |
| `tms9918.levels` | `COMPOSITE` 和 `DIFFERENCE`，即 Table 2-3 为每种颜色列出的信号电平，以及 `burst(model)` |
| `tms9918.__version__` | 已安装的版本 |

```python
import tms9918
from tms9918 import levels

for name, model in tms9918.MODELS.items():
    print(name, model.aliases, model.lines, model.output, model.clock_pins)

print(levels.COMPOSITE[0xF], levels.DIFFERENCE[0x4], levels.burst("tms9929a"))

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

`COMPOSITE` 将每个颜色索引映射到其亮度和色度电平，表中未列出色度处为 `None`。`DIFFERENCE` 将每个颜色索引映射到其亮度和两个色差电平。两者都按原样从 Table 2-3 复制而来。

### 各型号的帧长度

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

每款芯片的一帧都是每行 342 个点。复位后的第一个完整帧从一个 F 标志计到下一个 F 标志。

## 精灵与状态字节

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

五个精灵位于第 50 行。芯片绘制其中四个，设置 5S 标志并在低位写入第五个精灵的平面号 4；由于绘制的四个精灵相互重叠，它还设置了重合标志。

## 处理器的访问窗口

处理器只能在窗口中访问显存：在带精灵的 Graphics I 和 II 中每 16 个存储周期一次，在 Text 模式中每 3 个一次，在 Multicolor 中每 4 个一次，任何访问的等待时间都不超过约 8 微秒。手册没有说明每个窗口落在哪个点上。本包从 openMSX 的 MSX1 表中取得这些位置，并用 TI 列出的每一个界限对其进行测试。

openMSX 记录了在真实 MSX1 上的一次测量：间隔 26 个或更少处理器周期的数据写入会破坏显存，间隔 27 个或更多则从不会。本模型重现了这两种情况。第一次访问仍在等待时到达的第二次访问会替换它，所以上面的示例让每次写入都在下一次之前落入。

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

在一个 Graphics I 帧的有效显示期间，向 TMS9929A 写入三个字节。间隔 12 个点时，第二个字节在第一个字节找到窗口之前就已到达，因此第一个字节丢失，而地址已经前移。间隔 41 个点时，即超过以主时钟三分之一频率运行的处理器的 27 个周期，每个字节都能落入。

## 普查

```bash
python3 -m conformance.census /path/to/sg1000/library --frames 600 --jobs 10
```

普查在一块 SG-1000 主板上，用 `zilog-z80-python` 处理器启动 SG-1000 库中的每个镜像，并让每个镜像运行固定的帧数。它接受目录、zip 归档和单个镜像，并按摘要对每个不同的镜像只计数一次。它打印一份摘要，写入 [`conformance/corpus.json`](conformance/corpus.json)，并在某个属性被破坏时以 1 退出。

有些卡带自带 RAM，其中包括 Othello、The Castle 和台湾的 Dahjee 板。[`conformance/boards.json`](conformance/boards.json) 按照 MAME 的 SG-1000 软件列表的记录，以整个文件的 SHA-1 标识每个这样的镜像及其主板，测试框架将 RAM 映射到该主板放置它的位置。其他所有镜像都在普通主板上运行。

两个属性作为本次运行的门禁检查：模型在任何镜像上都不抛出异常，并且每个零售版镜像都会打开显示。在上一次访问得到服务之前就发出的访问会按镜像计数并列出，但不作为门禁检查，因为已发售的游戏确实会以超过窗口允许的速度写入，而芯片同样会丢失这些写入。改版、自制软件、翻译版、测试版、SC-3000 和 Master System 程序以及 BIOS 镜像从不参与门禁检查。

| 上一次运行的结果 | 数量 |
|:--|:--|
| 不同的镜像 | 348 |
| Graphics II | 279 |
| Graphics I | 47 |
| 设置了 Graphics II 位的 Text | 4 |
| Multicolor | 2 |
| Text | 1 |
| 从未打开显示，其中没有零售版 | 25 |
| 16 x 16 精灵，未放大 | 261 |
| 8 x 8 精灵 | 66 |
| 16 x 16 精灵，放大 | 4 |
| 零售版镜像上丢失的访问，全部来自 Champion Golf、Golgo 13 和 Sega-Galaga | 7 个镜像共 47 次 |
| 其余镜像上丢失的访问，几乎全部来自两款自制软件 | 12,629 |

[`conformance/corpus.json`](conformance/corpus.json) 保存了这些计数，不含任何卡带的内容，因此测试套件可以在没有库的机器上检查它们。

## 是否正确

TI 列出的、测试能够触及的每一项事实都与代码对照。[`conformance/hardware.json`](conformance/hardware.json) 记录每项事实及其原句和页码，[`conformance/hardware.test.py`](conformance/hardware.test.py) 将它们与包中的常量进行比较。`python3 -m conformance.quotes` 在手册中找出每一句引文。

手册未列出的每个值都放在同一文件的 `notStated` 下，标记为未验证，并附有其来源以及能够确定它的测量。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出了这些值。手册自相矛盾之处记录在 [`conformance/divergences.json`](conformance/divergences.json) 中。

## 参与开发

| 需求 | 位置 |
|:--|:--|
| 所有门禁检查及其运行顺序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 面向编码代理的同一份内容 | [AGENTS.md](AGENTS.md) |
| 本仓库与该系列其他仓库共享的标准 | [FAMILY.md](FAMILY.md) |
| 缺陷报告 | [GitHub Issues](https://github.com/gufranco/ti-tms9918-python/issues) |
| 安全报告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 tms9918/core.test.py
```

每个模块旁边都有一个以其命名的测试文件，每个测试文件都可以像上面那样单独运行。覆盖率是硬性门禁检查，要求语句和分支均达到 100%。

## 参考资料

- *TMS9918A/TMS9928A/TMS9929A Video Display Processors Data Manual*，Texas Instruments，1982 年 11 月。105 页，6,785,534 字节，SHA-256 `3991f0c691b83036bbb96d8e60e8d4ed4cfbb5eed9567ad61737570771113450`。该手册不可再分发，也不在本仓库中。`python3 -m conformance.documents` 从 https://bitsavers.org/components/ti/TMS9900/TMS9918A_TMS9928A_TMS9929A_Video_Display_Processors_Data_Manual_Nov82.pdf 下载它，并拒绝任何其他文件。
- openMSX，提交 `99c28389d775b945c57be27df1def0925e28abd8` 中的 `src/video/VDPAccessSlots.cc` 和 `src/video/VDP.hh`，https://github.com/openMSX/openMSX ，用于访问窗口的位置。只取事实，不取任何代码。
- MAME，提交 `dc00cf3517eef30587b33efbf1e1c63ad3531b58` 中的 `src/devices/video/tms9928a.cpp`，https://github.com/mamedev/mame ，用于手册和 openMSX 都未涵盖的行为；同一提交中的 `hash/sg1000.xml` 用于卡带主板。只取事实，不取任何代码。

## 引用本项目

[CITATION.cff](CITATION.cff) 在每次发布时由写入包版本号的脚本更新。

## 许可证

MIT。参见 [LICENSE](LICENSE)。
