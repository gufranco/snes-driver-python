# SNES Driver

读取 SNES 卡带为驱动其协处理器而运行的 65816 例程，并报告该例程对芯片的每一次访问，以清单所列卡带的驱动代码为准进行核对。

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-driver-python)](https://github.com/gufranco/snes-driver-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**42** 个卡带以四种摘要标识，**36** 个 DSP 卡带按 **2** 种布局读取，与自身摘要不符的 **0** 个，未与芯片通信的 **0** 个，**3** 种访问，**667** 个测试，**100%** 语句与分支覆盖率，无依赖

```python
from snesdriver import at, window_for

routine = bytes(
    [0xE2, 0x20, 0xA9, 0x01, 0x8F, 0x00, 0x60, 0x00]
    + [0xC2, 0x20, 0xAF, 0x00, 0x70, 0x00, 0xAF, 0x00, 0x60, 0x00, 0x60]
)

print(at(routine + bytes(2048), 0, window_for("dsp", "hirom")).shape)
```

```
write1 poll2 read2
```

该例程将累加器设为 8 位，在 `$00:6000` 存储一个字节，再将其设回 16 位，从 `$00:7000` 加载一个字，再从 `$00:6000` 加载一个字，然后返回。在高位卡带布局下，DSP 的数据寄存器在 `$6000` 响应，状态寄存器在 `$7000` 响应。因此这次交互是一个字节的命令、一次状态寄存器轮询和两个字节的应答。没有执行任何代码：每条指令都经过反汇编，并查询它访问到了哪里。

## 安装

| 要求 | 版本 |
|:--|:--|
| Python | 3.12 或更新 |
| git | 任意版本，用于获取两个子模块 |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-driver-python.git
cd snes-driver-python
python3 snesdriver/doctor.py
```

本包只导入标准库及其两个子模块。[`mos65xx-python`](https://github.com/gufranco/mos65xx-python) 负责反汇编 65816，[`snes-mapper-python`](https://github.com/gufranco/snes-mapper-python) 负责在卡带布局下解析地址。仓库页面上的下载 zip 链接给出的检出不含这两者，这样的检出在导入时会失败。对于未使用 `--recurse-submodules` 的检出，请运行 `git submodule update --init --recursive`。

本包未发布到任何包索引，[`pyproject.toml`](pyproject.toml) 也不含 `[project]` 块。wheel 无法携带子模块，因此它会安装成功，然后在首次导入时失败。

诊断脚本检查机器、子模块、清单和卡带库，最后输出一行结果。所有检查通过时退出码为 0，有一项未通过时为 1。提交 bug 报告时请粘贴其完整输出。

```
  16 checks, nothing to report
```

版本发布遵循 [语义化版本](https://semver.org/)，由 semantic-release 根据提交历史生成。每个版本都打有标签，并列在 [发布页面](https://github.com/gufranco/snes-driver-python/releases) 上。

## 接口

每个调用都接收卡带镜像的字节，并返回其代码访问到的内容。没有时钟，没有状态，也没有芯片模型。

### 芯片在哪里响应

| 名称 | 内容 |
|:--|:--|
| `window_for(part, layout)` | 该芯片在该布局下响应的 `Window`，若在该布局下没有窗口则为 `None`。对于 `WINDOWS` 中不存在的芯片名称，抛出 `UnknownPart` |
| `WINDOWS` | 所有窗口，先按芯片再按布局作为键 |
| `Window(first_bank, last_bank, data, status, end, status_end=None)` | 一个窗口。`status_end` 默认为 `end` |
| `window.reaches(bank, address)` | 对单个地址返回 `DATA`、`STATUS` 或 `None`。先检查状态范围 |
| `busiest(layout, reaches)` | 在 `layout` 下其窗口包含 `reaches` 中最多 `(bank, address)` 对的芯片，若没有任何窗口包含则为 `None` |
| `DATA`、`STATUS` | 字符串 `"data"` 和 `"status"` |
| `UnknownPart` | 由 `window_for` 抛出。消息列出所有芯片 |

| 芯片 | 布局 | Bank | 数据 | 状态 | 数据结束 | 状态结束 |
|:--|:--|:--|:--|:--|:--|:--|
| `dsp` | `lorom` | `$30-$3F` | `$8000` | `$C000` | `$FFFF` | `$FFFF` |
| `dsp` | `hirom` | `$00-$0F` | `$6000` | `$7000` | `$7FFF` | `$7FFF` |
| `st` | `lorom` | `$60-$67` | `$0000` | `$0001` | `$0001` | `$0001` |
| `st` | `lorom-shared` | `$68-$6F` | `$0000` | `$0020` | `$0FFF` | `$0021` |
| `obc1` | `lorom` | `$00-$3F` | `$6000` | `$7FF0` | `$7FFF` | `$7FFF` |
| `st018` | `lorom` | `$00-$3F` | `$3800` | `$3804` | `$3803` | `$3804` |

```python
import snesdriver

for part, layouts in sorted(snesdriver.WINDOWS.items()):
    for layout, window in sorted(layouts.items()):
        print(part, layout, window)

high = snesdriver.window_for("dsp", "hirom")
print(high.reaches(0x00, 0x6000), high.reaches(0x00, 0x7000), high.reaches(0x10, 0x6000))
print(snesdriver.window_for("obc1", "hirom"))
print(snesdriver.busiest("lorom", [(0x30, 0x8000), (0x30, 0xC000), (0x60, 0x0000)]))

try:
    snesdriver.window_for("sa1", "lorom")
except snesdriver.UnknownPart as error:
    print(error)
```

```
dsp hirom <Window $00-$0f:6000 data, 7000 status>
dsp lorom <Window $30-$3f:8000 data, c000 status>
obc1 lorom <Window $00-$3f:6000 data, 7ff0 status>
st lorom <Window $60-$67:0000 data, 0001 status>
st lorom-shared <Window $68-$6f:0000 data, 0020 status>
st018 lorom <Window $00-$3f:3800 data, 3804 status>
data status None
None
dsp
sa1 is not a part with a known window; there are dsp, obc1, st, st018
```

对于存在但在所查询布局下没有窗口的芯片，`window_for` 返回 `None`；对于没有任何芯片使用的名称，则抛出异常。`busiest` 在 `dsp` 窗口中计得两个地址，在 `st` 窗口中计得一个，因此它给出 `dsp`。

### 遍历例程

`through(rom, offset, narrow=True, limit=DEFAULT_LIMIT, address=None, bank=None, depth=8)` 从 `offset` 开始反汇编一个例程，并为每条指令产出一个 `Step`。

| 参数 | 含义 |
|:--|:--|
| `rom` | 以字节表示的镜像 |
| `offset` | 第一条指令的文件偏移 |
| `narrow` | 入口处的累加器宽度：`True` 表示 8 位，`False` 表示 16 位 |
| `limit` | 例程自身最多遍历的指令数。`DEFAULT_LIMIT` 为 80。被调用函数内的指令不计入，整个遍历在 `limit` 的 16 倍处停止 |
| `address` | `offset` 的 CPU 地址。默认为 `$8000` 加上 `offset` 对 `$8000` 取模 |
| `bank` | 例程运行所在的 bank。默认为 `offset` 除以 `$8000` |
| `depth` | 遍历跟随 `jsr` 和 `jsl` 的最大调用深度 |

遍历在例程自身中遇到第一个 `rts`、`rtl`、`rti`、`jmp`、`jml`、`bra`、`brl` 或 `stp` 时结束。指定累加器位的 `sep` 或 `rep` 会改变其后每次访问的宽度。只有当调用目标在 200 条指令内走到 `rts` 或 `rtl` 时才跟随该调用；其他调用会被跳过。

| `Step` 属性 | 含义 |
|:--|:--|
| `offset` | 指令的文件偏移 |
| `mnemonic` | 小写，例如 `sta` |
| `width` | 1 或 2，即累加器访问传送的字节数 |
| `narrow` | `width` 为 1 时为 True |
| `depth` | 例程自身中为 0，在其调用的函数内为 1，依此类推 |
| `bank` | 绝对或长访问到达的 bank，否则为 `None` |
| `address` | 绝对或长访问到达的 16 位地址，否则为 `None`。`pea` 和 `per` 不访问任何地址 |
| `banked` | 长访问时为 True，其 bank 写在指令中。绝对访问则使用例程自身的 bank |
| `reading` | 助记符以 `st` 开头时为 False，否则为 True |
| `immediate` | 立即数指令的操作数，否则为 `None` |
| `waiting` | 向后分支时为 True，例程正是以此等待寄存器 |

```python
from snesdriver import through

routine = bytes(
    [0xE2, 0x20, 0xA9, 0x01, 0x8F, 0x00, 0x60, 0x00, 0xC2, 0x20, 0x8F, 0x00, 0x60, 0x00, 0x60]
)

for step in through(routine + bytes(2048), 0):
    where = "-" if step.address is None else f"${step.bank:02x}:{step.address:04x}"
    print(f"{step.offset:#06x} {step.mnemonic} {step.width} {where} {step.banked}")
```

```
0x0000 sep 1 - False
0x0002 lda 1 - False
0x0004 sta 1 $00:6000 True
0x0008 rep 1 - False
0x000a sta 2 $00:6000 True
0x000e rts 2 - False
```

两条存储指令是相同的四个字节。第一条传送一个字节，因为它之前的 `sep #$20` 收窄了累加器；第二条传送两个字节，因为 `rep #$20` 又将其加宽。

### 读取交互

`at(rom, offset, window, narrow=True, limit=DEFAULT_LIMIT)` 用 `through` 遍历一个例程，并返回一个 `Conversation`，其中包含到达 `window` 的每一次访问。

| 类型 | 常量 | 访问属于此类型的条件 |
|:--|:--|:--|
| `write` | `WRITE` | 向数据寄存器或状态寄存器存储 |
| `read` | `READ` | 从数据寄存器加载 |
| `poll` | `POLL` | 从状态寄存器加载 |

| `Conversation` 属性 | 含义 |
|:--|:--|
| `shape` | 每次访问表示为其类型后接其宽度，以空格连接 |
| `steps` | 每次访问一条记录，包含 `what`、`width`、`bank`、`address`、`banked` 和 `whole`，即 24 位地址 |
| `covered` | 例程自身中遍历过的每条指令的文件偏移 |
| `written` | 写入的字节数 |
| `read` | 从数据寄存器读取的字节数 |
| `polls` | 例程至少轮询一次时为 True |
| `banked` | 每次访问都写明自己的 bank 时为 True |

没有任何访问到达窗口时，`Conversation` 为假。

```python
from snesdriver import at, shapes, sites, window_for

routine = bytes(
    [0xE2, 0x20, 0xA9, 0x01, 0x8F, 0x00, 0x60, 0x00]
    + [0xC2, 0x20, 0xAF, 0x00, 0x70, 0x00, 0xAF, 0x00, 0x60, 0x00, 0x60]
)
image = routine + bytes(2048)
window = window_for("dsp", "hirom")

talk = at(image, 0, window)
print(talk, talk.written, talk.read, talk.polls, talk.banked)
print(talk.steps)
print(sorted(talk.covered))
print([f"{one:#06x}" for one in sites(image, window)])
print(shapes(image, window))
```

```
<Conversation write1 poll2 read2> 1 2 True True
(<write 1>, <poll 2>, <read 2>)
[0, 2, 4, 8, 10, 14, 18]
['0x0004', '0x000a', '0x000e']
{'write1 poll2 read2': 1}
```

该例程有三个位点和一种形态。从第一个位点开始的遍历覆盖了另外两个，因此它们不会各自开始交互。

### 找出所有例程

| 调用 | 返回 |
|:--|:--|
| `sites(rom, window)` | 地址到达 `window` 的每条长加载（操作码 `$AF`）和长存储（操作码 `$8F`）的文件偏移。这是字节搜索：它也会在数据中找到这四个字节 |
| `reached(rom, window, entry=None, kind="lorom")` | 从十个原生模式和仿真模式向量，或从 `entry` 出发遍历时，到达 `window` 的每条指令的文件偏移，遍历会跟随每个目标写在指令中的调用、跳转和分支。`kind` 是将地址映射到文件偏移的布局。遍历在 400,000 条指令后停止 |
| `shapes(rom, window, narrow=True, limit=DEFAULT_LIMIT, find=sites)` | 每种不同的形态以及产生它的例程数量。`find` 返回的每个偏移都会用 `at` 开始一次遍历，除非之前的遍历已覆盖它 |

```python
from snesdriver import reached, shapes, sites, window_for

routine = bytes([0xE2, 0x20, 0xA9, 0x01, 0x8F, 0x00, 0x80, 0x30, 0xAF, 0x00, 0xC0, 0x30, 0x60])
image = bytearray(0x8000)
image[: len(routine)] = routine
image[0x0100:0x0104] = bytes([0x8F, 0x00, 0x80, 0x30])
image[0x7FFC:0x7FFE] = (0x8000).to_bytes(2, "little")
image = bytes(image)
window = window_for("dsp", "lorom")

print([f"{one:#06x}" for one in sites(image, window)])
print([f"{one:#06x}" for one in reached(image, window)])
print(shapes(image, window))
print(shapes(image, window, find=reached))
```

```
['0x0004', '0x0008', '0x0100']
['0x0004', '0x0008']
{'write1 poll1': 1, 'write1': 1}
{'write1 poll1': 1}
```

该镜像是一个低位卡带 bank，其复位向量指向该例程。`$0100` 处的四个字节构成一条到 DSP 的长存储，但从未被执行。`sites` 找到了它们，`reached` 则没有，因为从任何向量出发的遍历都不会到达那里。

### 模块内容

| 名称 | 内容 |
|:--|:--|
| `snesdriver.DEFAULT_LIMIT` | 80，即 `through`、`at` 和 `shapes` 的默认 `limit` |
| `snesdriver.VERSION`、`snesdriver.__version__` | 已安装的版本 |
| `snesdriver.walk.Step` | `through` 产出的类 |
| `snesdriver.conversation.Step` | `Conversation.steps` 中每个条目的类 |

### 命令

| 命令 | 参数 | 退出码 |
|:--|:--|:--|
| `python3 snesdriver/doctor.py` | 无 | 0 表示所有检查通过，1 表示有一项未通过 |
| `python3 -m conformance.against_cartridges` | 可选的目录，代替默认目录读取 | 0 表示每个卡带都与 DSP 通信，1 表示有一个卡带没有通信，2 表示未找到卡带 |
| `python3 -m conformance.speed` | 无 | 0 表示遍历超过每秒 20,000 个例程的下限，1 表示未超过 |
| `python3 -m conformance.links` | 无 | 本文件中有地址返回 HTTP 404 或 410 时为 1，否则为 0 |

## 为什么这无法猜测

SNES 协处理器向主机呈现一个数据寄存器和一个状态寄存器。一条命令占多少字节、返回多少字节，无法向芯片查询。这些芯片大多没有留存下来的数据手册。卡带为驱动芯片而运行的例程是唯一写下该协议的地方，本包读取的就是这个例程。

卡带只在其自身协议要求的位置轮询状态寄存器。以下是三个卡带各自一种形态的开头，按 `shapes` 的报告：

```text
Super Mario Kart   write1 write2 poll2 read2 read2 read2 read2 poll2 write2 ...
Pilotwings         poll1 write1 write2 write2 write2 read2 read2 write1 ...
Dungeon Master     write1 write1 write1 write1 write1 read1 read1 read1 read1
```

## 读取方式

例程从第一条指令遍历到第一条离开它的指令，并查询每条指令访问到了哪里。宽度不能跳过。一条存储指令传送一个字节还是两个字节取决于累加器，而累加器的宽度由之前的 `sep` 或 `rep` 设置，而非由存储指令本身决定。忽略它们的遍历会以错误的大小报告每次访问。

布局决定访问落在哪个寄存器上。DSP 在低位卡带中于 `$30-$3F:8000` 响应，在高位卡带中于 `$00-$0F:6000` 响应。选择状态寄存器的地址线在前一种情况下是第 14 位，在后一种情况下是第 12 位。

## 使用你自己的卡带

每个卡带先由其 `sha256` 识别，然后在反汇编任何一个字节之前，用其 `crc32`、`md5` 和 `sha1` 进行确认。`sha256` 匹配而其他摘要不匹配的文件会使扫描以错误终止。清单中没有的文件会被跳过。直接对这样的文件调用 `conformance.cartridges.identify` 时，它会指出可能的原因：拷贝机文件头、字节交换、已知的坏 dump 或修改过的发行版。

将你拥有的副本放在 [`cartridges/`](cartridges/README.md)、本仓库旁边的 `cartridges` 目录，或 `SNES_CARTRIDGE_DIR` 指向的位置。该变量未设置时，先尝试同级目录。[`cartridges/README.md`](cartridges/README.md) 列出每个文件名和全部四种摘要，[`cartridges.manifest.json`](cartridges.manifest.json) 以程序可读的形式保存相同内容。仓库中没有任何内容会重建卡带的任何部分。

## 每项证据的价值

| 证据 | 能确定什么 | 不能确定什么 |
|:--|:--|:--|
| 卡带自身的代码，逐条指令遍历 | 已发售的游戏向芯片发送什么 | 任何游戏都不发送的内容 |
| 65816 指令集，经由反汇编器 | 每条指令是什么，其访问有多宽 | 另一端芯片的任何情况 |
| 文件头声明的布局，经由映射器 | 哪些地址到达芯片 | 到达时会发生什么 |
| 每个读取卡带的四种摘要 | 读取的文件就是所指名的文件 | 该发行版是否就是你想要的那个 |

形态并不说明芯片如何应答。这属于为各芯片建模的成员项目，例如 [`snes-dsp-python`](https://github.com/gufranco/snes-dsp-python)。

## 它是否正确

```bash
python3 -m conformance.against_cartridges
```

扫描读取它找到的每个卡带，并打印每个卡带的布局、位点数、形态数及其最常见的四种形态。在作者的卡带库上，它读取了 36 个 DSP 卡带，其中 0 个没有通信。其中三个：

| 卡带 | 布局 | 位点 | 不同形态 |
|:--|:--|--:|--:|
| Super Mario Kart (USA) | hirom | 122 | 18 |
| Pilotwings (USA) | lorom | 122 | 17 |
| Dungeon Master (USA) | lorom | 130 | 13 |

清单中其余 6 个卡带搭载 `st`、`st018` 和 `obc1` 芯片。扫描只读取 DSP，而这 6 个卡带都不在所读取的卡带库中。没有卡带时，扫描以 2 退出。CI 在每次推送时运行它，将退出码 2 视为跳过并加以标注。

[`conformance/hardware.json`](conformance/hardware.json) 记录每个窗口及其依据，[`conformance/hardware.test.py`](conformance/hardware.test.py) 让 `WINDOWS` 与其保持一致。没有窗口被标记为已验证，因为没有任何厂商文档给出卡带电路板为协处理器解码的地址线。[`conformance/divergences.json`](conformance/divergences.json) 记录某个来源比表面上更不可靠的地方，[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出每个未知项以及能够确定它的测量。

## 参与开发

| 需求 | 位置 |
|:--|:--|
| 每项门禁检查及其运行顺序，供编码代理使用 | [AGENTS.md](AGENTS.md) |
| 本仓库与家族中其他仓库共用的标准 | [FAMILY.md](FAMILY.md) |
| Bug 报告 | [GitHub Issues](https://github.com/gufranco/snes-driver-python/issues) |
| 安全报告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
pnpm run format:check
python3 -m coverage erase
for file in $(find snesdriver conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
python3 -m conformance.speed
```

每个模块旁边都有一个名为 `<module>.test.py` 的测试文件，每个都可单独运行。覆盖率是一道硬性门禁检查，要求 100% 语句与分支覆盖，无论机器上有无卡带库。吞吐量下限在覆盖率步骤之外运行。提交遵循 [约定式提交](https://www.conventionalcommits.org/)。

## 参考资料

- 未使用任何厂商文档。Nintendo 的开发手册 Book I 记录了内存映射和文件头，但没有记录卡带电路板为协处理器解码的地址线。Book II 中的 DSP-1 应用说明能确定这些窗口。
- [`mos65xx-python`](https://github.com/gufranco/mos65xx-python)，取子模块固定的提交，用于 65816 指令集。
- [`snes-mapper-python`](https://github.com/gufranco/snes-mapper-python)，取子模块固定的提交，用于卡带布局。
- 作者拥有的零售版卡带库，用于所读取的 36 个卡带。其中任何内容都未提交。

## 引用

[CITATION.cff](CITATION.cff) 在每次发布时由标记包版本的脚本更新。

## 许可证

MIT。参见 [LICENSE](LICENSE)。
