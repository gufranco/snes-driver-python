# SNES Driver

SNESカートリッジがコプロセッサを駆動するために実行する65816ルーチンを読み取り、そのパーツへのすべてのアクセスを報告します。結果は、マニフェストに記載されたカートリッジのドライバコードと照合されています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-driver-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-driver-python)](https://github.com/gufranco/snes-driver-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

4つのダイジェストで特定されたカートリッジ**42**本、ヘッダーが示すパーツで読み取ったカートリッジ**42**本、自身のダイジェストとの不一致**0**件、パーツに何も送らなかったもの**0**本、アクセスの種類**3**種、テスト**815**件、ステートメントとブランチのカバレッジ**100%**、依存関係なし

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

このルーチンはアキュムレータを8ビットにし、`$00:6000`に1バイトをストアし、16ビットに戻し、`$00:7000`から1ワード、`$00:6000`から1ワードをロードして、リターンします。ハイカートリッジのレイアウトでは、DSPのデータレジスタは`$6000`で、ステータスレジスタは`$7000`で応答します。したがってこのやり取りは、1バイトのコマンド、ステータスレジスタのポーリング、2バイトの応答です。何も実行していません。各命令を逆アセンブルし、どこに到達するかを調べただけです。

## インストール

| 要件   | バージョン                                |
| :----- | :---------------------------------------- |
| Python | 3.12以降                                  |
| git    | 任意。2つのサブモジュールの取得に使います |

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-driver-python.git
cd snes-driver-python
python3 snesdriver/doctor.py
```

このパッケージは、標準ライブラリと2つのサブモジュール以外は何もインポートしません。[`mos65xx-python`](https://github.com/gufranco/mos65xx-python)は65816を逆アセンブルし、[`snes-mapper-python`](https://github.com/gufranco/snes-mapper-python)はカートリッジのレイアウトのもとでアドレスを解決します。リポジトリページのzipダウンロードリンクで得られるチェックアウトにはどちらも含まれず、そのチェックアウトはインポート時に失敗します。`--recurse-submodules`なしで作成したチェックアウトでは、`git submodule update --init --recursive`を実行してください。

このパッケージはパッケージインデックスに登録されておらず、[`pyproject.toml`](pyproject.toml)には`[project]`ブロックがありません。wheelはサブモジュールを含められないため、インストールはできても最初のインポートで失敗します。

ドクターはマシン、サブモジュール、マニフェスト、カートリッジライブラリをチェックし、最後に1行を出力します。すべてのチェックに合格すると0で、1つでも不合格なら1で終了します。バグ報告には、その出力全体を貼り付けてください。

```
  16 checks, nothing to report
```

リリースは[Semantic Versioning](https://semver.org/)に従い、semantic-releaseがコミット履歴から作成します。すべてのリリースにはタグが付けられ、[リリースページ](https://github.com/gufranco/snes-driver-python/releases)に掲載されます。

## インターフェース

どの呼び出しもカートリッジイメージのバイト列を受け取り、そのコードが到達するものを返します。クロックも状態も、パーツのモデルもありません。

### パーツが応答する場所

| 名前                                                                                | 内容                                                                                                                                   |
| :---------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| `window_for(part, layout)`                                                          | そのレイアウトでそのパーツが応答する`Window`。そこにウィンドウがない場合は`None`。`WINDOWS`にないパーツ名には`UnknownPart`を送出します |
| `WINDOWS`                                                                           | すべてのウィンドウ。パーツ、次にレイアウトをキーとします                                                                               |
| `Window(first_bank, last_bank, data, status, end, status_end=None, mirrored=False)` | 1つのウィンドウ。`status_end`のデフォルトは`end`です。`mirrored`のウィンドウはビット7を立てたバンクでも応答します                      |
| `window.reaches(bank, address)`                                                     | 1つのアドレスについて`DATA`、`STATUS`、または`None`。ステータスの範囲が先に判定されます                                                |
| `busiest(layout, reaches)`                                                          | `layout`でのウィンドウが`reaches`内の`(bank, address)`ペアを最も多く含むパーツ。どのウィンドウも1つも含まない場合は`None`              |
| `DATA`、`STATUS`                                                                    | 文字列`"data"`と`"status"`                                                                                                             |
| `UnknownPart`                                                                       | `window_for`が送出します。メッセージにはすべてのパーツが列挙されます                                                                   |

| パーツ  | レイアウト     | バンク               | データ  | ステータス | データの終端 | ステータスの終端 |
| :------ | :------------- | :------------------- | :------ | :--------- | :----------- | :--------------- |
| `dsp`   | `lorom`        | `$30-$3F`, `$B0-$BF` | `$8000` | `$C000`    | `$BFFF`      | `$FFFF`          |
| `dsp`   | `hirom`        | `$00-$0F`, `$80-$8F` | `$6000` | `$7000`    | `$6FFF`      | `$7FFF`          |
| `st`    | `lorom`        | `$60-$67`            | `$0000` | `$0001`    | `$0001`      | `$0001`          |
| `st`    | `lorom-shared` | `$68-$6F`            | `$0000` | `$0020`    | `$0FFF`      | `$0021`          |
| `obc1`  | `lorom`        | `$00-$3F`, `$80-$BF` | `$6000` | `$7FF0`    | `$7FFF`      | `$7FFF`          |
| `st018` | `lorom`        | `$00-$3F`            | `$3800` | `$3804`    | `$3803`      | `$3804`          |

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

`window_for`は、存在するパーツでも指定したレイアウトにウィンドウがなければ`None`を返し、どのパーツの名前でもない場合は例外を送出します。`busiest`は`dsp`のウィンドウに2つ、`st`のウィンドウに1つのアドレスを数えるので、`dsp`を返します。

### ルーチンをたどる

`through(rom, offset, narrow=None, limit=DEFAULT_LIMIT, address=None, bank=None, depth=8, index=None, known=None, ran=False)`は、`offset`から1つのルーチンを逆アセンブルし、命令ごとに`Step`をyieldします。

| 引数      | 意味                                                                                                                                                 |
| :-------- | :--------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rom`     | バイト列としてのイメージ                                                                                                                             |
| `offset`  | 最初の命令のファイルオフセット                                                                                                                       |
| `narrow`  | 入口でのアキュムレータ幅。8ビットなら`True`、16ビットなら`False`、分からなければ`None`（デフォルト）                                                 |
| `limit`   | ルーチン自体でたどる命令の最大数。`DEFAULT_LIMIT`は80です。呼び出し先の命令は数えず、全体のたどりは`limit`の16倍で停止します                         |
| `address` | `offset`のCPUアドレス。デフォルトは`$8000`に`offset`を`$8000`で割った余りを足した値です                                                              |
| `bank`    | ルーチンが実行されるバンク。デフォルトは`offset`を`$8000`で割った値です                                                                              |
| `depth`   | `jsr`と`jsl`を何段の呼び出しまで追うか                                                                                                               |
| `index`   | 入口でのインデックスレジスタの幅。`narrow`と同じ表し方                                                                                               |
| `known`   | `widths`が各ファイルオフセットで見つけた幅。たどりが飛ばした呼び出しの後では、次の命令で見つかった組がちょうど1つならそれを使います                  |
| `ran`     | `narrow`がコードの設定した幅ではなく、イメージの実行で使われた幅であるときTrue。コードがアキュムレータの幅を設定するまで、各ステップがこれを持ちます |

たどりは、ルーチン自体の中で最初の`rts`、`rtl`、`rti`、`jmp`、`jml`、`bra`、`brl`、`stp`で終わります。アキュムレータのビットを指定する`sep`または`rep`は、それ以降のすべてのアクセスの幅を変えます。呼び出しは、呼び出し先が200命令以内に`rts`または`rtl`に到達する場合にのみ追い、それ以外の呼び出しは飛ばし、その後の2つの幅は、呼び出しの次の命令について`known`がちょうど1組を持つ場合を除き不明になります。

| `Step`の属性 | 意味                                                                                                             |
| :----------- | :--------------------------------------------------------------------------------------------------------------- |
| `offset`     | 命令のファイルオフセット                                                                                         |
| `mnemonic`   | `sta`のような小文字                                                                                              |
| `width`      | 1または2。アキュムレータのアクセスが移動するバイト数。アキュムレータの幅が分からない間は`None`                   |
| `narrow`     | `width`が1のときTrue、分からないときは`None`                                                                     |
| `depth`      | ルーチン自体では0、そこからの呼び出しの中では1、以下同様                                                         |
| `bank`       | 絶対アクセスまたはロングアクセスが到達するバンク。それ以外は`None`                                               |
| `address`    | 絶対アクセスまたはロングアクセスが到達する16ビットアドレス。それ以外は`None`。`pea`と`per`はどこにも到達しません |
| `banked`     | ロングアクセスのときTrue。バンクが命令内に明記されています。絶対アクセスは代わりにルーチン自身のバンクを使います |
| `reading`    | `st`で始まるニーモニックならFalse、それ以外はTrue                                                                |
| `immediate`  | イミディエート命令のオペランド。それ以外は`None`                                                                 |
| `waiting`    | 後方への分岐のときTrue。ルーチンはこの方法でレジスタを待ちます                                                   |
| `ran`        | `width`がイメージの実行で使われた幅である間はTrue。コードがアキュムレータの幅を設定するまで続きます              |

`narrow`で指定しない限り、たどりはアキュムレータの幅が分からない状態で始まります。アキュムレータのビットを指定する`sep`や`rep`がそれを設定し、`php`が保存して対応する`plp`が復元します。ルーチン内で何も保存していない`plp`は、幅を再び不明にします。インデックスレジスタの幅も、インデックスのビットを指定する`sep`と`rep`を通じて同じように運ばれます。その長さを決める幅が分からない間に出会った即値命令は長さが分からないため、たどりはそこで終わります。

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

2つのストアは同じ4バイトです。1つ目は直前の`sep #$20`がアキュムレータを狭めたので1バイトを移動し、2つ目は`rep #$20`が再び広げたので2バイトを移動します。

### やり取りを読む

`at(rom, offset, window, narrow=None, limit=DEFAULT_LIMIT, index=None, known=None, ran=False, traced=None)`は`through`で1つのルーチンをたどり、`window`に到達したすべてのアクセスを保持する`Conversation`を返します。`traced`は、命令のファイルオフセットを、トレースした実行でその命令が動かしたバイト数に対応付けます。たどりが幅を知らないアクセスはそこでその幅を取り、トークンに`~`が付きます。

| 種類    | 定数    | アクセスがこの種類になる条件                       |
| :------ | :------ | :------------------------------------------------- |
| `write` | `WRITE` | データレジスタまたはステータスレジスタにストアする |
| `read`  | `READ`  | データレジスタからロードする                       |
| `poll`  | `POLL`  | ステータスレジスタからロードする                   |

| `Conversation`の属性 | 意味                                                                                                                                |
| :------------------- | :---------------------------------------------------------------------------------------------------------------------------------- |
| `shape`              | 各アクセスを種類と幅で表し、分からなければ`?`、実行が使った幅の後には`*`、トレースが見た幅の後には`~`を付け、スペースで連結したもの |
| `steps`              | アクセスごとに1件のレコード。`what`、`width`、`bank`、`address`、`banked`、24ビットアドレスの`whole`を持ちます                      |
| `covered`            | ルーチン自体でたどったすべての命令のファイルオフセット                                                                              |
| `written`            | 書き込んだバイト数                                                                                                                  |
| `read`               | データレジスタから読み取ったバイト数                                                                                                |
| `polls`              | ルーチンが少なくとも1回ポーリングするときTrue                                                                                       |
| `banked`             | すべてのアクセスが自身のバンクを明記しているときTrue                                                                                |

ウィンドウに何も到達しなかった場合、`Conversation`は偽になります。

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

このルーチンにはサイトが3つ、シェイプが1つあります。最初のサイトからのたどりが残りの2つを含むので、それらは独自のやり取りを開始しません。

### すべてのルーチンを見つける

| 呼び出し                                                                                              | 戻り値                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| :---------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sites(rom, window)`                                                                                  | アドレスが`window`に到達するすべてのロングロード（オペコード`$AF`）とロングストア（オペコード`$8F`）のファイルオフセット。バイト検索なので、データ内にあるその4バイトも見つけます                                                                                                                                                                                                                                                                                                                                                                                |
| `reached(rom, window, entry=None, kind="lorom")`                                                      | ネイティブモードとエミュレーションモードの10個のベクタ、または`entry`からのたどりで`window`に到達するすべての命令のファイルオフセット。行き先が命令内に明記されたすべての呼び出し、ジャンプ、分岐を追います。`kind`はアドレスをファイルオフセットに対応付けるレイアウトです。たどりは400,000命令で止まります                                                                                                                                                                                                                                                     |
| `widths(rom, kind="lorom", entry=None, limit=400000)`                                                 | ベクタからのたどりが逆アセンブルした各ファイルオフセットと、そこに到達したときの`(narrow, index)`の組。分からなかった幅は`None`                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `shapes(rom, window, narrow=None, limit=DEFAULT_LIMIT, find=sites, kind=None, ran=None, traced=None)` | 異なるシェイプそれぞれと、それを生むルーチンの数。`find`が返す各オフセットは、それ以前のたどりが含んでいない限り、`at`でのたどりを開始します。`kind`を渡すと、各たどりはそのオフセットについて`widths`が見つけたすべての幅で始まり、2つの幅で入られるルーチンはそれぞれにシェイプを持ちます。何も見つからなかった場合は、ファイルオフセットから実行がそこで使った組への対応である`ran`の幅がそれを確定させ、シェイプは`*`で示します。`traced`はすべての`at`に渡されるので、まだ幅の分からないアクセスはその命令でトレースが見た幅を取り、シェイプは`~`で示します |

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
print(shapes(image, window, kind="lorom", traced={0x0100: 2}))
```

```
['0x0004', '0x0008', '0x0100']
['0x0004', '0x0008']
{'write? poll?': 1, 'write?': 1}
{'write? poll?': 1}
frozenset({(True, True)})
{'write1 poll1': 1, 'write?': 1}
{'write1 poll1': 1, 'write2*': 1}
{'write1 poll1': 1, 'write2~': 1}
```

このイメージはローカートリッジの1バンクで、リセットベクタがルーチンを指しています。`$0100`の4バイトはDSPへのロングストアを表しますが、実行されることはありません。`sites`はそれを見つけますが、`reached`は見つけません。どのベクタからのたどりもそこに到達しないからです。レイアウトを渡すと、`shapes`はルーチンが8ビット幅で実行されることを知ります。リセットはプロセッサをエミュレーションモードにし、ストアの前に幅を広げるものがないからです。それでも`$0100`の幅は分からず、それを確定できるのは実行だけです。スタブのコンソールでの実行は`*`で、そこでのストアが2バイト動かしたのを見たトレースは`~`で、それを確定させます。前者はたどりが始まったときにプロセッサが持っていた幅であり、後者はその1つの命令でバスが行ったことで、その後のアクセスについては何も言いません。

ベクタからのたどりは、すべての呼び出しを通じて両方の幅を運びます。呼び出し先には、呼び出し元が残した幅ごとに1回ずつ入り、呼び出し元は呼び出し先が戻るときの各幅で再開します。テーブル経由の呼び出し、イメージ外への呼び出し、戻るところをたどりが見ない呼び出し先への呼び出しは、コードが幅を示さないため、両方の幅を不明のままにします。

### モジュールの内容

| 名前                                           | 内容                                                 |
| :--------------------------------------------- | :--------------------------------------------------- |
| `snesdriver.DEFAULT_LIMIT`                     | 80。`through`、`at`、`shapes`の`limit`のデフォルト値 |
| `snesdriver.VERSION`、`snesdriver.__version__` | インストールされているバージョン                     |
| `snesdriver.walk.Step`                         | `through`がyieldするクラス                           |
| `snesdriver.sweep`                             | `reached`と`widths`の背後にあるベクタからのたどり    |
| `snesdriver.conversation.Step`                 | `Conversation.steps`の各要素のクラス                 |

### コマンド

| コマンド                                                      | 引数                                                                                          | 終了コード                                                                                                                                    |
| :------------------------------------------------------------ | :-------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------- |
| `python3 snesdriver/doctor.py`                                | なし                                                                                          | すべてのチェックに合格で0、1つでも不合格で1                                                                                                   |
| `python3 -m conformance.against_cartridges`                   | デフォルトの代わりに読み取るディレクトリ（任意）                                              | すべてのカートリッジがヘッダーの示すパーツと通信すれば0、何も送らないものがあれば1、カートリッジが見つからなければ2                           |
| `python3 -m conformance.speed`                                | なし                                                                                          | たどりが毎秒20,000ルーチンの下限を上回れば0、下回れば1                                                                                        |
| `python3 -m conformance.executed <image> [budget] [--widths]` | カートリッジイメージ、実行する命令数（デフォルトは2,000,000）、幅を代わりに出力する`--widths` | 実行してパーツに届いたすべての命令を出力すれば0、ヘッダーがウィンドウのあるパーツを示さなければ1、イメージが指定されなければ2                 |
| `python3 -m conformance.traced`                               | 既定の代わりに読むディレクトリ（省略可）                                                      | トレースできたすべてのカートリッジをトレースすれば0、実行が失敗すれば1、エミュレータもカートリッジもないか、トレースできるものが何もなければ2 |
| `python3 -m conformance.links`                                | なし                                                                                          | このファイル内のアドレスがHTTP 404または410を返せば1、それ以外は0                                                                             |

`conformance.executed`はイメージを読み取る代わりに65816で実行します。相手のコンソールは、`$4210`と`$4212`の交互に切り替わるブランキングビットを除くすべてのレジスタに0を返し、20,000命令ごとと、プログラムがNMIを待つたびにNMIを発生させます。報告されるのは下限です。その実行で実際にパーツに届いた命令であり、読み取りではたどれない経路を確定させますが、実行が通らなかった経路については何も言いません。`--widths`を付けると、代わりに1つのJSONオブジェクトを出力します。パーツに届いた各命令のファイルオフセットを、そこでプロセッサが持っていた`[narrow, index]`の組に対応付けたもので、`shapes`が受け取る`ran`です。

`conformance.traced`は見つけた各カートリッジを、ヘッドレスのMAMEで`SDL_VIDEODRIVER=dummy mame snes -window -video none -sound none -nothrottle`として2回実行します。1回目はコントローラーに触れずに3,600フレーム、2回目は30フレームごとに1つのボタンを3フレーム押し、Start、A、Start、B、Down、A、Up、Start、A、Rightの順に替えながら7,200フレームです。[`conformance/traced.lua`](conformance/traced.lua)は、各バンクとそのミラーバンクでパーツのウィンドウのすべてのアドレスをタップし、各アクセスをプログラムカウンタ、ステータスレジスタ、データバンク、ダイレクトページとともに記録します。1つの命令が1.5マイクロ秒以内に連続するアドレスへ行う2つのアクセスは、2バイトの1つのアクセスです。各アクセスはその後カートリッジ自身のバイトと照合されます。記録されたプログラムカウンタで終わる命令を、記録されたMとXのフラグで逆アセンブルし、そのオペランドがアドレスを示し、そのフラグの下でオペコードが動かす幅がバスの動かした幅と一致しなければなりません。通ったものは[`conformance/traced.json`](conformance/traced.json)のサイトになり、命令のファイルオフセットとそれが動かしたすべての幅を持ちます。通らなかったものは不一致として残り、不一致を持つサイトは決して使われません。ファームウェアを持つパーツは、`SNES_FIRMWARE_DIR`が示すディレクトリにそれが必要で、ダイジェストで見つけてイメージの後ろに付けます。MAMEはそのように読みます。`MAME_ROMPATH`は、MAMEがコンソール自身のROMを見つける場所を示します。`mame`やカートリッジがなければ2で終了します。このコーパスはエミュレータの段です。各実行がどの経路を通るかはMAMEの65816とMAMEのパーツのモデルが決め、どの実行も通らなかった経路は`?`のままです。

## 推測できない理由

SNESのコプロセッサは、本体に対してデータレジスタとステータスレジスタを見せます。コマンドが何バイトを受け取り何バイトを返すかは、パーツに問い合わせることができません。これらのパーツの多くには、現存するデータシートがありません。カートリッジがパーツを駆動するために実行するルーチンが、プロトコルが書き残されている唯一の場所であり、このパッケージはそのルーチンを読み取ります。

カートリッジは、自身のプロトコルが必要とする箇所でのみステータスレジスタをポーリングします。3本のカートリッジそれぞれから1つのシェイプの冒頭を、レイアウトを渡したときに`shapes`が報告するとおりに示します。

```text
Super Mario Kart   write? write2 poll2 read2 read2 read2 read2 poll2 write2 ...
Pilotwings         write? write2 write2 write2 read2 read2 write1 write2 write2 ...
Dungeon Master     write1 write1 write1 write1 write1 read1 read1 read1 read1
```

`?`は、このパッケージが読み取れる範囲ではコードが幅を決めていないアクセスです。各たどりは検索が見つけたアクセスから、その前にあった`sep`や`rep`の後で、ベクタからのたどりがそこに到達したときの幅で始まります。ほとんどのドライバルーチンは、ジャンプテーブルのようにそのたどりが追えないものを経由して入られるため、ほとんどは今も`?`で始まります。上のDungeon Masterのルーチンは、そのたどりが8ビット幅で到達するものです。

MAMEで実行すると、カートリッジは残りの一部を確定させます。[`conformance/traced.json`](conformance/traced.json)は、トレースした実行でパーツに届いた3,104の命令を保持し、スイープはたどりが幅を持たないところでそこから幅を取り、`~`で示します。42本のカートリッジ全体で、5,160の交換のうち`?`を持つのは4,874になり、トレースなしでは5,103です。7,853のアクセスでは6,549で、トレースなしでは6,945です。DSPカートリッジのうち6本はどちらの実行でもパーツに届かなかったため、トレースはそれらについて何も言いません。

## 読み取りの仕組み

ルーチンは最初の命令から、ルーチンを抜ける最初の命令までたどられ、各命令がどこに到達したかを調べます。幅は省略できません。ストアが1バイトを移動するか2バイトを移動するかはアキュムレータで決まり、アキュムレータの幅はストアではなく、それ以前の`sep`または`rep`で設定されます。これらを無視するたどりは、すべてのアクセスを誤ったサイズで報告することになります。

アクセスがどのレジスタに届くかはレイアウトで決まります。NintendoのBook IIの図3-1-4と図3-1-5が記載するとおり、DSPはローカートリッジでは`$30-$3F:8000`と`$B0-$BF:8000`で、ハイカートリッジでは`$00-$0F:6000`と`$80-$8F:6000`で応答します。ステータスレジスタを選択するアドレス線は、前者ではビット14、後者ではビット12です。

## 自分のカートリッジを使う

すべてのカートリッジは、1バイトでも逆アセンブルする前に、`sha256`で特定され、続いて`crc32`、`md5`、`sha1`で確認されます。`sha256`が一致して他のダイジェストが一致しないファイルは、エラーでスイープを停止させます。マニフェストにないファイルはスキップされます。そのようなファイルに対して`conformance.cartridges.identify`を直接呼び出すと、コピー機のヘッダ、バイトの入れ替わり、既知の不良ダンプ、改変されたリリースといった、考えられる原因を示します。

所有しているコピーを、[`cartridges/`](cartridges/README.md)、このリポジトリと同じ階層の`cartridges`ディレクトリ、または`SNES_CARTRIDGE_DIR`が指す場所に置いてください。この変数が未設定の場合は、同じ階層のディレクトリが最初に試されます。[`cartridges/README.md`](cartridges/README.md)にはすべてのファイル名と4つのダイジェストすべてが記載されており、[`cartridges.manifest.json`](cartridges.manifest.json)は同じ内容をプログラムが読める形式で保持しています。リポジトリ内のものは、カートリッジのどの部分も再構成しません。

## 各証拠の価値

| 証拠                                              | 確定できること                                   | 確定できないこと                   |
| :------------------------------------------------ | :----------------------------------------------- | :--------------------------------- |
| 命令ごとにたどったカートリッジ自身のコード        | 出荷されたゲームがパーツに何を送るか             | どのゲームも送らないもの           |
| 逆アセンブラを通した65816の命令セット             | 各命令が何であり、そのアクセスの幅がどれだけか   | 相手側のパーツについてのこと       |
| マッパーを通した、ヘッダが宣言するレイアウト      | どのアドレスがパーツに到達するか                 | 到達したときに何が起きるか         |
| 読み取ったすべてのカートリッジの4つのダイジェスト | 読み取ったファイルが指定されたファイルであること | そのリリースが意図したものかどうか |

シェイプは、パーツが何を応答するかについては何も示しません。それは[`snes-dsp-python`](https://github.com/gufranco/snes-dsp-python)のような、各パーツをモデル化するファミリーのメンバーの役割です。

## 正しいか

```bash
python3 -m conformance.against_cartridges
```

スイープは見つかったすべてのカートリッジを読み取り、それぞれのレイアウト、サイト数、シェイプ数、最も頻度の高い4つのシェイプを出力し、続いてパーツごとに、交換の数、まだ`?`を持つものの数、`~`を持つものの数を1行で出力します。作者のライブラリでは42本すべてのカートリッジを、それぞれヘッダーが示すパーツで読み取り、何も送らなかったものは0本でした。そのうち4本を示します。最後の1本はOBC1を搭載しています。

| カートリッジ                          | レイアウト | サイト | 異なるシェイプ |
| :------------------------------------ | :--------- | -----: | -------------: |
| Super Mario Kart (USA)                | hirom      |    127 |             25 |
| Pilotwings (USA)                      | lorom      |    212 |             25 |
| Dungeon Master (USA)                  | lorom      |    192 |             16 |
| Metal Combat - Falcon's Revenge (USA) | lorom      |    313 |             18 |

スイープはカートリッジタイプのバイトからパーツを決めます。その上位ニブルをコプロセッサに割り当てているのは、Book Iの1-2-18ページの表です。カスタムチップは`$FFBF`のサブナンバーで区別し、マニフェストにある4本のカスタムチップのカートリッジは、ST010とST011では1、ST018では2を設定しています。カートリッジがない場合、スイープは2で終了します。CIはプッシュのたびにこれを実行し、終了コード2をスキップとして扱い、注記を付けます。

[`conformance/hardware.json`](conformance/hardware.json)はすべてのウィンドウをその根拠となる証拠とともに記録し、[`conformance/hardware.test.py`](conformance/hardware.test.py)は`WINDOWS`がそれに一致することを確認します。2つのDSPウィンドウは検証済みとされています。Book IIが両方を記載しているからです。それ以外のウィンドウは検証済みではありません。カートリッジ基板がST010、ST011、ST018、OBC1のためにデコードするアドレス線を示すメーカー文書がないからです。[`conformance/divergences.json`](conformance/divergences.json)は情報源が見かけより弱い箇所を記録し、[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)は未解決の事項それぞれを、それを確定できる測定とともに列挙しています。

## 開発に参加する

| 必要なもの                                                   | 場所                                                                   |
| :----------------------------------------------------------- | :--------------------------------------------------------------------- |
| コーディングエージェント向けの、すべてのゲートとその実行順序 | [AGENTS.md](AGENTS.md)                                                 |
| このリポジトリがファミリーの他のリポジトリと共有する標準     | [FAMILY.md](FAMILY.md)                                                 |
| バグ報告                                                     | [GitHub Issues](https://github.com/gufranco/snes-driver-python/issues) |
| セキュリティ報告                                             | [SECURITY.md](SECURITY.md)                                             |

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

各モジュールの隣には`<module>.test.py`という名前のテストファイルがあり、それぞれ単独で実行できます。カバレッジは、カートリッジライブラリがあるマシンでもないマシンでも、ステートメントとブランチの100%を必須とするゲートです。スループットの下限はカバレッジのステップとは別に実行されます。コミットは[Conventional Commits](https://www.conventionalcommits.org/)に従います。

## 参考文献

- Nintendoの_SNES Development Manual, Book II_。図3-1-4と図3-1-5の2つのDSPウィンドウに使い、テキストレイヤーには見出ししかないためスキャンページから読み取りました。アーカイブされたテキストは463,516バイトでSHA-256は`546f8e38caf6cb19c8aa9d5a1fef090d8cfc4a0a13b54c3b56d704975ab8398a`、テキストレイヤー付きのスキャンは29,575,127バイトでSHA-256は`05197923d9b73b63845fc5c2d609e753ec634dc1e4b403ce7a57326e1259c3ed`です。どちらもこのリポジトリには含まれておらず、https://archive.org/details/SNESDevManual にあります。Book Iはメモリマップとヘッダを記載していますが、カートリッジ基板がコプロセッサのためにデコードするアドレス線は記載していません。
- [`mos65xx-python`](https://github.com/gufranco/mos65xx-python)。サブモジュールが固定するコミットのもので、65816の命令セットに使います。
- [`snes-mapper-python`](https://github.com/gufranco/snes-mapper-python)。サブモジュールが固定するコミットのもので、カートリッジのレイアウトに使います。
- MAME 0.289。ヘッドレスで実行し、`conformance/traced.json`の幅に使います。エミュレータなので、それが示すものはエミュレータの段に立ち、使われるところではすべて`~`で示します。
- 作者が所有する市販カートリッジのライブラリ。読み取った42本のカートリッジに使います。そこからは何もコミットしていません。

## 引用

[CITATION.cff](CITATION.cff)は、パッケージのバージョンを刻むスクリプトによって、リリースごとに更新されます。

## ライセンス

MIT。[LICENSE](LICENSE)を参照してください。
