# SNES Driver

讀取 SNES 卡帶為驅動其協處理器而執行的 65816 例程，並報告該例程對該部件的每一次存取，結果以清單所列卡帶的驅動程式碼為準。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![CI](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-driver-python)](https://github.com/gufranco/snes-driver-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**42** 個卡帶以四種摘要識別，**42** 個卡帶按各自標頭所指的部件讀取，與自身摘要不符者 **0** 個，未向部件發出任何存取者 **0** 個，**3** 種存取，**746** 項測試，**100%** 語句及分支覆蓋率，無依賴套件

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

該例程把累加器設為 8 位元，在 `$00:6000` 存入一個位元組，再把累加器設回 16 位元，從 `$00:7000` 載入一個字，再從 `$00:6000` 載入一個字，然後返回。在高位卡帶佈局下，DSP 的數據暫存器在 `$6000` 回應，狀態暫存器在 `$7000` 回應。因此這次交換是一個位元組的命令、一次對狀態暫存器的輪詢，以及兩個位元組的回應。沒有任何指令被執行：每條指令都經過反組譯，並查明它存取到哪裏。

## 安裝

| 要求   | 版本                         |
| :----- | :--------------------------- |
| Python | 3.12 或更新                  |
| git    | 任何版本，用於取得兩個子模組 |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-driver-python.git
cd snes-driver-python
python3 snesdriver/doctor.py
```

本套件除標準函式庫及其兩個子模組外不匯入任何東西。[`mos65xx-python`](https://github.com/gufranco/mos65xx-python) 負責反組譯 65816，[`snes-mapper-python`](https://github.com/gufranco/snes-mapper-python) 負責在某種卡帶佈局下解析位址。儲存庫頁面上的下載 zip 連結所得的副本不含這兩個子模組，該副本在匯入時會失敗。若副本建立時沒有使用 `--recurse-submodules`，請執行 `git submodule update --init --recursive`。

本套件沒有發佈到任何套件索引，[`pyproject.toml`](pyproject.toml) 也沒有 `[project]` 區塊。wheel 無法攜帶子模組，因此它能安裝，卻會在第一次匯入時失敗。

診斷腳本會檢查機器、子模組、清單及卡帶庫，最後輸出一行結果。所有檢查通過時以 0 結束，有一項未通過時以 1 結束。提交錯誤報告時，請貼上其完整輸出。

```
  16 checks, nothing to report
```

版本遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根據提交歷史發佈。每個版本都有標籤，並列於[版本頁面](https://github.com/gufranco/snes-driver-python/releases)。

## 介面

每個呼叫都接受一個卡帶映像檔的位元組，並返回其程式碼所存取到的東西。沒有時鐘，沒有狀態，也沒有任何部件的模型。

### 部件在哪裏回應

| 名稱                                                                                | 內容                                                                                                                        |
| :---------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------- |
| `window_for(part, layout)`                                                          | 該部件在該佈局下回應的 `Window`；若該部件在該佈局下沒有窗口，則為 `None`。若部件名稱不在 `WINDOWS` 中，則拋出 `UnknownPart` |
| `WINDOWS`                                                                           | 所有窗口，先以部件、再以佈局為鍵                                                                                            |
| `Window(first_bank, last_bank, data, status, end, status_end=None, mirrored=False)` | 一個窗口。`status_end` 預設為 `end`。`mirrored` 的窗口在第 7 位元設定的 bank 中同樣回應                                     |
| `window.reaches(bank, address)`                                                     | 對單一位址返回 `DATA`、`STATUS` 或 `None`。先檢查狀態範圍                                                                   |
| `busiest(layout, reaches)`                                                          | 在 `layout` 下，其窗口包含 `reaches` 中最多 `(bank, address)` 對的部件；若沒有窗口包含任何一對，則為 `None`                 |
| `DATA`, `STATUS`                                                                    | 字串 `"data"` 及 `"status"`                                                                                                 |
| `UnknownPart`                                                                       | 由 `window_for` 拋出。訊息列出所有現有部件                                                                                  |

| 部件    | 佈局           | 記憶庫               | 數據    | 狀態    | 數據結束 | 狀態結束 |
| :------ | :------------- | :------------------- | :------ | :------ | :------- | :------- |
| `dsp`   | `lorom`        | `$30-$3F`, `$B0-$BF` | `$8000` | `$C000` | `$BFFF`  | `$FFFF`  |
| `dsp`   | `hirom`        | `$00-$0F`, `$80-$8F` | `$6000` | `$7000` | `$6FFF`  | `$7FFF`  |
| `st`    | `lorom`        | `$60-$67`            | `$0000` | `$0001` | `$0001`  | `$0001`  |
| `st`    | `lorom-shared` | `$68-$6F`            | `$0000` | `$0020` | `$0FFF`  | `$0021`  |
| `obc1`  | `lorom`        | `$00-$3F`, `$80-$BF` | `$6000` | `$7FF0` | `$7FFF`  | `$7FFF`  |
| `st018` | `lorom`        | `$00-$3F`            | `$3800` | `$3804` | `$3803`  | `$3804`  |

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
dsp hirom <Window $00-$0f,$80-$8f:6000 data, 7000 status>
dsp lorom <Window $30-$3f,$b0-$bf:8000 data, c000 status>
obc1 lorom <Window $00-$3f,$80-$bf:6000 data, 7ff0 status>
st lorom <Window $60-$67:0000 data, 0001 status>
st lorom-shared <Window $68-$6f:0000 data, 0020 status>
st018 lorom <Window $00-$3f:3800 data, 3804 status>
data status None
None
dsp
sa1 is not a part with a known window; there are dsp, obc1, st, st018
```

對於存在但在所查詢佈局下沒有窗口的部件，`window_for` 返回 `None`；對於沒有任何部件使用的名稱，則拋出異常。`busiest` 在 `dsp` 窗口中數到兩個位址，在 `st` 窗口中數到一個，因此它返回 `dsp`。

### 走訪例程

`through(rom, offset, narrow=None, limit=DEFAULT_LIMIT, address=None, bank=None, depth=8, index=None, known=None, ran=False)` 從 `offset` 開始反組譯一個例程，每條指令產生一個 `Step`。

| 參數      | 含義                                                                                                                 |
| :-------- | :------------------------------------------------------------------------------------------------------------------- |
| `rom`     | 以位元組表示的映像檔                                                                                                 |
| `offset`  | 第一條指令的檔案偏移                                                                                                 |
| `narrow`  | 進入時的累加器寬度：`True` 為 8 位元，`False` 為 16 位元，未知時為 `None`（預設）                                    |
| `limit`   | 在例程本身中最多走訪的指令數。`DEFAULT_LIMIT` 為 80。被呼叫者內部的指令不計算在內，整個走訪在 `limit` 的 16 倍處停止 |
| `address` | `offset` 的處理器位址。預設為 `$8000` 加上 `offset` 除以 `$8000` 的餘數                                              |
| `bank`    | 例程所在的記憶庫。預設為 `offset` 除以 `$8000`                                                                       |
| `depth`   | 走訪跟隨 `jsr` 及 `jsl` 的呼叫深度                                                                                   |
| `index`   | 入口處變址暫存器的寬度，表示方式與 `narrow` 相同                                                                     |
| `known`   | `widths` 在每個檔案偏移處找到的寬度。走訪跳過一個呼叫之後，如果下一條指令處恰好找到一組，就採用它                    |
| `ran`     | 當 `narrow` 是映像檔執行時使用的寬度而不是程式碼設定的寬度時為 True。在程式碼設定累加器寬度之前，每一步都帶有它      |

走訪在例程本身中遇到第一個 `rts`、`rtl`、`rti`、`jmp`、`jml`、`bra`、`brl` 或 `stp` 時結束。指明累加器位元的 `sep` 或 `rep` 會改變其後每次存取的寬度。只有當呼叫目標能在 200 條指令內走到 `rts` 或 `rtl` 時，才會跟隨該呼叫；其他呼叫則會跳過，之後兩個寬度都未知，除非 `known` 對呼叫後的下一條指令恰好有一組。

| `Step` 屬性 | 含義                                                                           |
| :---------- | :----------------------------------------------------------------------------- |
| `offset`    | 指令的檔案偏移                                                                 |
| `mnemonic`  | 小寫，例如 `sta`                                                               |
| `width`     | 1 或 2，即一次累加器存取搬動的位元組數；累加器寬度未知時為 `None`              |
| `narrow`    | `width` 為 1 時為 True，未知時為 `None`                                        |
| `depth`     | 在例程本身中為 0，在其呼叫內部為 1，如此類推                                   |
| `bank`      | 絕對或長存取所到達的記憶庫，否則為 `None`                                      |
| `address`   | 絕對或長存取所到達的 16 位元位址，否則為 `None`。`pea` 及 `per` 不存取任何位址 |
| `banked`    | 長存取時為 True，其記憶庫寫在指令之中。絕對存取則使用例程本身的記憶庫          |
| `reading`   | 助記符以 `st` 開頭時為 False，否則為 True                                      |
| `immediate` | 立即數指令的運算元，否則為 `None`                                              |
| `waiting`   | 向後分支時為 True，例程正是以此等待暫存器                                      |
| `ran`       | 當 `width` 是映像檔執行時使用的寬度時為 True，直到程式碼設定累加器寬度為止     |

除非 `narrow` 另有說明，走訪開始時累加器寬度未知。指明累加器位元的 `sep` 或 `rep` 設定它，`php` 保存它，與之對應的 `plp` 恢復它；例程內沒有保存過的 `plp` 會令它重新變為未知。變址暫存器的寬度亦以同樣方式經由指明變址位元的 `sep` 和 `rep` 傳遞。決定其長度的寬度未知時遇到的立即數指令長度無法確定，因此走訪在那裏結束。

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
0x0000 sep None - False
0x0002 lda 1 - False
0x0004 sta 1 $00:6000 True
0x0008 rep 1 - False
0x000a sta 2 $00:6000 True
0x000e rts 2 - False
```

兩次存入是相同的四個位元組。第一次搬動一個位元組，因為之前的 `sep #$20` 把累加器收窄；第二次搬動兩個位元組，因為 `rep #$20` 再次把它加寬。

### 讀取交換

`at(rom, offset, window, narrow=None, limit=DEFAULT_LIMIT, index=None, known=None, ran=False)` 用 `through` 走訪一個例程，並返回一個 `Conversation`，其中包含每一次到達 `window` 的存取。

| 種類    | 常數    | 存取屬於此種類的條件       |
| :------ | :------ | :------------------------- |
| `write` | `WRITE` | 存入數據暫存器或狀態暫存器 |
| `read`  | `READ`  | 從數據暫存器載入           |
| `poll`  | `POLL`  | 從狀態暫存器載入           |

| `Conversation` 屬性 | 含義                                                                                           |
| :------------------ | :--------------------------------------------------------------------------------------------- |
| `shape`             | 每次存取以其種類及寬度表示，未知時為 `?`，執行所用的寬度後加 `*`，以空格連接                   |
| `steps`             | 每次存取一條記錄，包含 `what`、`width`、`bank`、`address`、`banked` 及 `whole`，即 24 位元位址 |
| `covered`           | 例程本身中所有已走訪指令的檔案偏移                                                             |
| `written`           | 寫入的位元組數                                                                                 |
| `read`              | 從數據暫存器讀取的位元組數                                                                     |
| `polls`             | 例程至少輪詢一次時為 True                                                                      |
| `banked`            | 每次存取都寫明自身記憶庫時為 True                                                              |

當沒有任何存取到達窗口時，`Conversation` 為假。

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
{'write? poll2 read2': 1}
```

該例程有三個位置和一種形態。從第一個位置開始的走訪已覆蓋另外兩個，因此它們不會各自開始新的交換。

### 找出所有例程

| 呼叫                                                                                     | 返回                                                                                                                                                                                                                                                                                                         |
| :--------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sites(rom, window)`                                                                     | 每個位址到達 `window` 的長載入（操作碼 `$AF`）及長存入（操作碼 `$8F`）的檔案偏移。這是位元組搜尋：它也會在數據中找到這四個位元組                                                                                                                                                                             |
| `reached(rom, window, entry=None, kind="lorom")`                                         | 從十個原生及模擬模式向量或從 `entry` 開始走訪時，每條到達 `window` 的指令的檔案偏移；走訪會跟隨每個目標寫在指令中的呼叫、跳轉及分支。`kind` 是把位址對應到檔案偏移的佈局。走訪在 400,000 條指令後停止                                                                                                        |
| `widths(rom, kind="lorom", entry=None, limit=400000)`                                    | 由向量開始的走訪所反組譯的每個檔案偏移，以及到達該處時的 `(narrow, index)` 組，未知的寬度為 `None`                                                                                                                                                                                                           |
| `shapes(rom, window, narrow=None, limit=DEFAULT_LIMIT, find=sites, kind=None, ran=None)` | 每種不同的形態及產生它的例程數目。`find` 返回的每個偏移都會以 `at` 開始一次走訪，除非先前的走訪已覆蓋它。給定 `kind` 時，每次走訪都以 `widths` 為其偏移找到的每個寬度開始，以兩種寬度進入的例程各有一種形態。如果甚麼也沒找到，`ran` 中的寬度（由檔案偏移到執行在該處所用組的對應）會確定它，形態以 `*` 標示 |

```python
from snesdriver import reached, shapes, sites, widths, window_for

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
print(widths(image, "lorom")[0x0004])
print(shapes(image, window, kind="lorom"))
print(shapes(image, window, kind="lorom", ran={0x0100: frozenset({(False, True)})}))
```

```
['0x0004', '0x0008', '0x0100']
['0x0004', '0x0008']
{'write? poll?': 1, 'write?': 1}
{'write? poll?': 1}
frozenset({(True, True)})
{'write1 poll1': 1, 'write?': 1}
{'write1 poll1': 1, 'write2*': 1}
```

該映像檔是一個低位卡帶記憶庫，其重設向量指向該例程。`$0100` 處的四個位元組構成一條對 DSP 的長存入，但從未被執行。`sites` 找到它們，`reached` 則找不到，因為沒有任何從向量開始的走訪會到達那裏。給定佈局後，`shapes` 知道該例程以 8 位元寬度執行，因為重設令處理器處於模擬模式，存入之前亦沒有任何指令把它加寬。它仍然無法知道 `$0100` 處的寬度，只有執行才能確定。

由向量開始的走訪會經過每個呼叫傳遞兩個寬度。被呼叫者按每個呼叫者留下的寬度各進入一次，呼叫者則按被呼叫者返回時的每個寬度恢復。經由表的呼叫、呼叫到映像檔之外，以及走訪從未看到其返回的被呼叫者，都會令兩個寬度保持未知，因為程式碼沒有說明它們是多少。

### 模組內容

| 名稱                                           | 內容                                              |
| :--------------------------------------------- | :------------------------------------------------ |
| `snesdriver.DEFAULT_LIMIT`                     | 80，即 `through`、`at` 及 `shapes` 的預設 `limit` |
| `snesdriver.VERSION`, `snesdriver.__version__` | 已安裝的版本                                      |
| `snesdriver.walk.Step`                         | `through` 產生的類別                              |
| `snesdriver.sweep`                             | `reached` 及 `widths` 背後由向量開始的走訪        |
| `snesdriver.conversation.Step`                 | `Conversation.steps` 中每個項目的類別             |

### 命令

| 命令                                                          | 參數                                                                      | 結束代碼                                                                       |
| :------------------------------------------------------------ | :------------------------------------------------------------------------ | :----------------------------------------------------------------------------- |
| `python3 snesdriver/doctor.py`                                | 無                                                                        | 0 所有檢查通過，1 有一項未通過                                                 |
| `python3 -m conformance.against_cartridges`                   | 可選的目錄，用以代替預設目錄讀取                                          | 0 所有卡帶都與其標頭所指的部件通訊，1 有一個卡帶沒有任何存取，2 找不到任何卡帶 |
| `python3 -m conformance.speed`                                | 無                                                                        | 0 走訪速度超過每秒 20,000 個例程的下限，1 未超過                               |
| `python3 -m conformance.executed <image> [budget] [--widths]` | 卡帶映像檔，要執行的指令數，預設 2,000,000，以及改為列出寬度的 `--widths` | 0 已執行並列出每條到達部件的指令，1 標頭所指的部件沒有窗口，2 沒有指定映像檔   |
| `python3 -m conformance.links`                                | 無                                                                        | 本檔案中有位址回應 HTTP 404 或 410 時為 1，否則為 0                            |

`conformance.executed` 在 65816 上執行映像檔而不是讀取它。與它配合的主機對每個暫存器都傳回 0，只有 `$4210` 和 `$4212` 的消隱位元交替變化，並且每 20,000 條指令以及程式每次等待時都觸發 NMI。它報告的是下限：那次執行中真正到達部件的指令，能確定讀取無法追蹤的路徑，但對執行沒有走過的路徑甚麼也說明不了。加上 `--widths` 時，它改為列出一個 JSON 物件，把每條到達部件的指令的檔案偏移對應到處理器在該處持有的 `[narrow, index]` 組，這就是 `shapes` 接受的 `ran`。

## 為何無法靠猜測得知

SNES 協處理器向主機顯示一個數據暫存器和一個狀態暫存器。一個命令需要多少位元組、返回多少位元組，無法向部件查詢。這些部件大多沒有留存下來的數據表。卡帶為驅動部件而執行的例程，是唯一記載該協議的地方，而本套件讀取的正是該例程。

卡帶只會在其自身協議要求的時刻輪詢狀態暫存器。以下是三個卡帶各一種形態的開頭，按給定佈局時 `shapes` 的報告列出：

```text
Super Mario Kart   write? write2 poll2 read2 read2 read2 read2 poll2 write2 ...
Pilotwings         write? write2 write2 write2 read2 read2 write1 write2 write2 ...
Dungeon Master     write1 write1 write1 write1 write1 read1 read1 read1 read1
```

`?` 是在本套件能讀到的範圍內，程式碼沒有決定其寬度的存取。每次走訪都由搜尋找到的存取開始，位於其之前的 `sep` 或 `rep` 之後，使用由向量開始的走訪到達該處時的寬度。大多數驅動例程經由該走訪無法跟隨的途徑（例如跳轉表）進入，所以大多數仍以 `?` 開頭。上面 Dungeon Master 的例程是該走訪以 8 位元寬度到達的一個。

## 讀取方式

例程從第一條指令走訪到第一條離開例程的指令，並查明每條指令存取到哪裏。寬度不能略過。一次存入搬動一個還是兩個位元組取決於累加器，而累加器的寬度由較早的 `sep` 或 `rep` 設定，並非由存入指令設定。忽略它們的走訪會以錯誤的大小報告每次存取。

佈局決定存取落在哪個暫存器上。正如 Nintendo 的 Book II 圖 3-1-4 和圖 3-1-5 所印，DSP 在低位卡帶中於 `$30-$3F:8000` 和 `$B0-$BF:8000` 回應，在高位卡帶中於 `$00-$0F:6000` 和 `$80-$8F:6000` 回應。選擇狀態暫存器的位址線，在前者是第 14 位元，在後者是第 12 位元。

## 使用你自己的卡帶

每個卡帶都以其 `sha256` 識別，並在反組譯任何位元組之前，以其 `crc32`、`md5` 及 `sha1` 確認。若檔案的 `sha256` 相符而其他摘要不符，會以錯誤停止掃描。清單不認識的檔案會被略過。直接對這類檔案呼叫 `conformance.cartridges.identify`，它會指出可能的原因：複製機標頭、位元組互換、已知的壞傾印或經修改的版本。

把你擁有的副本放在 [`cartridges/`](cartridges/README.md)、本儲存庫旁邊的 `cartridges` 目錄，或 `SNES_CARTRIDGE_DIR` 所指的位置。未設定該變數時，會先嘗試旁邊的目錄。[`cartridges/README.md`](cartridges/README.md) 列出每個檔案名稱及全部四種摘要，[`cartridges.manifest.json`](cartridges.manifest.json) 以程式可讀的形式保存相同內容。儲存庫中沒有任何東西會重建卡帶的任何部分。

## 各項證據的價值

| 證據                           | 能確定的                         | 不能確定的                 |
| :----------------------------- | :------------------------------- | :------------------------- |
| 卡帶本身的程式碼，逐條指令走訪 | 已發行遊戲向部件發送甚麼         | 沒有遊戲發送的任何東西     |
| 65816 指令集，經由反組譯器     | 每條指令是甚麼，以及其存取有多寬 | 另一端部件的任何事情       |
| 標頭聲明的佈局，經由映射器     | 哪些位址到達部件                 | 到達時會發生甚麼           |
| 每個讀取的卡帶的四種摘要       | 讀取的檔案就是所指名的檔案       | 該版本是否就是你想要的版本 |

形態並不說明部件會回應甚麼。那屬於模擬各部件的家族成員，例如 [`snes-dsp-python`](https://github.com/gufranco/snes-dsp-python)。

## 結果正確嗎

```bash
python3 -m conformance.against_cartridges
```

掃描會讀取找到的每個卡帶，並列出每個卡帶的佈局、位置數目、形態數目及最常見的四種形態。在作者的卡帶庫上，它讀取了全部 42 個卡帶，每個都按其標頭所指的部件讀取，其中 0 個沒有存取。其中四個，最後一個搭載 OBC1：

| 卡帶                                  | 佈局  | 位置 | 不同形態 |
| :------------------------------------ | :---- | ---: | -------: |
| Super Mario Kart (USA)                | hirom |  127 |       19 |
| Pilotwings (USA)                      | lorom |  212 |       21 |
| Dungeon Master (USA)                  | lorom |  192 |       14 |
| Metal Combat - Falcon's Revenge (USA) | lorom |  313 |       14 |

掃描從卡帶類型位元組決定部件：Book I 第 1-2-18 頁的表把它的高四位元分配給協處理器。定製晶片以 `$FFBF` 的子編號區分，清單中的四個定製晶片卡帶對 ST010 和 ST011 設為 1，對 ST018 設為 2。沒有任何卡帶時，掃描以 2 結束。CI 在每次推送時執行它，把結束代碼 2 視為略過並加上註記。

[`conformance/hardware.json`](conformance/hardware.json) 記錄每個窗口及其背後的證據，[`conformance/hardware.test.py`](conformance/hardware.test.py) 以此約束 `WINDOWS`。兩個 DSP 窗口被標記為已驗證，因為 Book II 印出了兩者。其他窗口都沒有，因為沒有任何製造商文件說明卡帶電路板為 ST010、ST011、ST018 或 OBC1 解碼的位址線。[`conformance/divergences.json`](conformance/divergences.json) 記錄來源比表面看來更弱的地方，[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出每個未知之處及能夠確定它的測量方法。

## 參與開發

| 需要                                     | 位置                                                                   |
| :--------------------------------------- | :--------------------------------------------------------------------- |
| 給程式編寫代理的所有關卡檢查及其執行順序 | [AGENTS.md](AGENTS.md)                                                 |
| 本儲存庫與家族其他成員共用的標準         | [FAMILY.md](FAMILY.md)                                                 |
| 錯誤報告                                 | [GitHub Issues](https://github.com/gufranco/snes-driver-python/issues) |
| 安全報告                                 | [SECURITY.md](SECURITY.md)                                             |

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

每個模組旁邊都有一個名為 `<module>.test.py` 的測試檔案，各自可獨立執行。覆蓋率是硬性關卡檢查：在有卡帶庫的機器和沒有卡帶庫的機器上，語句及分支覆蓋率都必須達到 100%。吞吐量下限在覆蓋率步驟之外執行。提交遵循 [Conventional Commits](https://www.conventionalcommits.org/)。

## 參考資料

- Nintendo 的 _SNES Development Manual, Book II_，用於圖 3-1-4 和圖 3-1-5 中的兩個 DSP 窗口，因文字層只有標題而從掃描頁讀出。存檔文字為 463,516 位元組，SHA-256 為 `546f8e38caf6cb19c8aa9d5a1fef090d8cfc4a0a13b54c3b56d704975ab8398a`；附文字層的掃描為 29,575,127 位元組，SHA-256 為 `05197923d9b73b63845fc5c2d609e753ec634dc1e4b403ce7a57326e1259c3ed`。兩者都不在本儲存庫中，都位於 https://archive.org/details/SNESDevManual 。Book I 記載了記憶體映射和標頭，但沒有記載卡帶電路板為協處理器解碼的位址線。
- [`mos65xx-python`](https://github.com/gufranco/mos65xx-python)，採用子模組所固定的提交，用於 65816 指令集。
- [`snes-mapper-python`](https://github.com/gufranco/snes-mapper-python)，採用子模組所固定的提交，用於卡帶佈局。
- 作者擁有的零售版卡帶庫，用於所讀取的 42 個卡帶。其中任何內容都沒有提交。

## 引用本專案

[CITATION.cff](CITATION.cff) 會在每次發佈時，由標記套件版本的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。
