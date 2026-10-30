# D4 实测报告：产物密封（`seal_run.py`）的全捕获与隐藏面

- **卡**：XJ-20261030-002 / D4
- **采集日期**：2026-10-30
- **采集者**：minimax code（本卡实现者）
- **对象**：`tools/eval/seal_run.py`（SHA-256 清单封装工具，红区文件，本次只读调用）
- **实验目录**：`dryrun/d4/`（临时，未跟踪，不在触碰面内）

---

## 0. 结论

> ## 密封副本完整性：`OK`——run-dir 内的产物被全量捕获，逐项校验通过
> ## 隐藏产物路径：**已列明**（7 类，见 §4），其中 2 类会直接影响第四轮的可比性
>
> 摘要：`products/<task-id>/` 下的实现文件、嵌套子目录、隐藏文件、以及**落在 run-dir
> 内的 run-log 文件**全部进入 SHA-256 清单；改一个字节、加一个文件、删一个文件
> 三种改动都被 `--verify` 检出；custody 副本与原目录对封一致。
> 拍不到的是**run-dir 之外**的一切（执行者工作区、`%TEMP%`、app 缓存、会话库），
> 以及**目录形态**与**文件元数据**类信息。

本报告不宣称第四轮可开跑；结论汇总见卡内 `## dry-run 结论`。

---

## 1. 实测方法

按协议 §13.1 的目录约定搭一个 run-dir（`run-data.json` + `products/<task-id>/…`），
外加若干**故意放在 run-dir 之外**的产物与**空目录**，然后：

1. 密封 → 检查清单覆盖了哪些路径；
2. `--verify` 未改目录 → 应为 OK；
3. 改一个已封文件 → 应报 `MODIFIED`；
4. 加一个新文件 → 应报 `ADDED`；
5. 删一个已封文件 → 应报 `MISSING`；
6. `--move-to` 复制到 custody → 副本应对封一致；
7. 构造一个**整体替换**的目录 → 观察其是否「干净通过」。

复跑命令：

```powershell
python dryrun/d4/seal_capture_probe.py        # exit 0
python dryrun/d4/seal_addendum_probe.py       # exit 0
```

---

## 2. 实测结果

### 2.1 密封清单（5 个文件，全部在 run-dir 内）

```
  manifest file_count=5
    products/T11/.hidden_artifact
    products/T11/fib.py
    products/T11/sub/nested.txt
    products/T12/answer.md
    run-data.json
```

→ `products/<task-id>/` 的**递归全量**、**嵌套子目录**、**隐藏文件**全部进入清单。

### 2.2 三种改动均被检出

```
--- verify the untouched sealed run dir ---
  exit=0
  VERIFY: OK (5 files match the seal)

--- verify after modifying products/T11/fib.py ---
  exit=1
  MODIFIED  products/T11/fib.py
  VERIFY: DRIFT (1 finding(s))

--- verify after adding products/T11/added_later.py ---
  exit=1
  MODIFIED  products/T11/fib.py
  ADDED  products/T11/added_later.py
  VERIFY: DRIFT (2 finding(s))

--- verify after deleting products/T12/answer.md ---
  exit=1
  MODIFIED  products/T11/fib.py
  MISSING  products/T12/answer.md
  ADDED  products/T11/added_later.py
  VERIFY: DRIFT (3 finding(s))
```

### 2.3 custody 副本

```
  seal: ...\dryrun\d4\run\seal.json
  root_label: dryrun-d4-custody
  files: 5
  custody: ...\dryrun\d4\custody\run (copy verified against the seal)
```

→ 复制（而非移动）后，副本对封一致；执行者原目录保持在原处（工具设计如此）。

### 2.4 拒绝无 run-data.json 的目录

```
  exit=2
  [ERROR] seal refused: refusing to seal ...\dryrun\d4\no-run-data: run-data.json missing
  (seal targets a run directory produced by study_runner)
```

→ 误封普通目录的形态被挡住。

### 2.5 整体替换（工具自述的已知洞，本次复核仍成立）

```
  seal exit=0 / verify exit=0
  VERIFY: OK (2 files match the seal)
```

→ 一个**内容不同但自洽**的目录可以干净通过封签校验。与 `seal_run.py` 文件头
「tamper-evident, not tamper-proof」的自述一致：清单反映的是**内容不变**，
不是**来源同一**；绑定 run 与产物的链条是 custody 规程，不是哈希。

### 2.6 追加实测：run-log 与 junction

```
  manifest files:
    linked_outside/secret_outside.txt
    run-data.json
    run-log-exec.json
```

→ （a）**run-log 落在 run-dir 内时会随 run 一起被封**（协议 §13.2 指定的
`<run-dir>/run-log-exec.json` 位置成立）——这条使 run-log 与产物受同一封签保护；
（b）run-dir 内的**目录 junction**：其**内容**按 junction 路径进入清单并被哈希，
但被指向的**外部文件本身**不在清单中，且 junction 改指**内容相同**的另一文件时
哈希不变（不可检出）。

---

## 3. 核对表（脚本原样输出）

```
=== checks ===
  [PASS] sealed: products/T11/fib.py
  [PASS] sealed: products/T11/sub/nested.txt
  [PASS] sealed: products/T11/.hidden_artifact
  [PASS] sealed: products/T12/answer.md
  [PASS] seal.json itself is not in its own manifest
  [PASS] empty dir products/T20/empty_dir is not recorded (no file to hash)
  [PASS] artifact written OUTSIDE run-dir is not sealed (workspace/stray.py)
  [PASS] artifact written to TEMP is not sealed
  [PASS] verify on untouched dir reports OK
  [PASS] modify a sealed file is detected (MODIFIED)
  [PASS] add a file after sealing is detected (ADDED)
  [PASS] delete a sealed file is detected (MISSING)
  [PASS] custody copy verifies against the seal
  [PASS] a substituted directory verifies clean (tamper-EVIDENT only, not tamper-PROOF)

=== checks (追加) ===
  [PASS] run-log-exec.json inside the run dir IS sealed
  [PASS] junction target file appears under the junction path
  [PASS] the OUTSIDE file's own path is not in the manifest
```

---

## 4. 密封拍不到的隐藏产物路径（逐项列明）

| # | 隐藏面 | 判据 | 对第四轮的影响 | 处置建议 |
|---|---|---|---|---|
| H1 | **run-dir 之外的任何文件**（执行者工作区 `%TEMP%`、app 缓存、`~/.minimax` 会话库与 sqlite、`%APPDATA%\MiniMax` 日志） | 实测：`workspace/stray.py`、`%TEMP%\dryrun-d4-temp-artifact.txt` 均不在清单 | **高**：执行者若把实现写在 run-dir 外，该实现**没有任何封签**，判定读不到它 | 协议 §13.1 的目录约定即为此而设；执行卡须写明「一切实现文件必须落在 `products/<task-id>/`」并做落位检查 |
| H2 | **空目录** | 实测：`products/T20/empty_dir` 不在清单 | 低：无内容即无证据 | 无需处置（登记即可） |
| H3 | **目录形态本身**（目录树结构、空目录的存在/消失） | 实测：清单只记文件路径 | 低 | 无需处置 |
| H4 | **文件元数据**（mtime、ACL、属主、备用数据流 ADS） | 实测：清单只记 `sha256` + `bytes` | 低—中：无法核实「文件未被改权限」 | 登记为已知边界 |
| H5 | **junction / 符号链接的真实落点** | 实测：内容按链接路径入清单，外部真身不在清单；改指同内容文件不可检出 | 中 | 执行卡禁止在 run-dir 内使用 junction/符号链接 |
| H6 | **整体替换目录**（自洽清单） | 实测：替换目录 `--verify` 通过（exit 0） | **高**：封签不绑定「来源同一」 | 必须执行 custody 规程：`seal.json` 与 custody 副本分开保管，seal 由不在执行者可写路径上的主体持有（工具文件头已自述此为程序性而非密码学缓解） |
| H7 | **密封时刻之后新增的文件** | 实测：`ADDED` 可检出——但**前提是有人再跑一次 `--verify`** | 中：若不跑 verify，新增不可见 | 执行卡须写明「密封后必须立即 verify 一次并留档」 |

---

## 5. 与 D3 的联动

- D3 §4 指出：网络下载落临时目录、执行者自带工具写盘等**不进 run-dir**，
  因而**也不进密封**（H1）。这两条缺口指向同一处：第四轮的「产物」面若不强制
  落在 run-dir 内，密封与判定都看不到它。
- 反向的正面读数：run-log 若放在 run-dir 内，则**执行痕迹与产物受同一封签保护**
  （§2.6），满足 v1.3 约束 2 的口径。

---

## 6. 复跑配方

评审可直接在仓内复跑：

```powershell
# 1) 搭 run-dir（run-data.json + products/<task-id>/…）后密封
python tools/eval/seal_run.py dryrun/d4/run --label dryrun-d4
# -> exit 0；打印 files: N

# 2) 校验
python tools/eval/seal_run.py --verify dryrun/d4/run
# -> exit 0；VERIFY: OK (N files match the seal)

# 3) 改一个字节后校验（应报 MODIFIED，exit 1）
# 4) 加一个文件后校验（应报 ADDED，exit 1）
# 5) 删一个文件后校验（应报 MISSING，exit 1）

# 6) 密封并复制到 custody（副本自动对封）
python tools/eval/seal_run.py dryrun/d4/run --label dryrun-d4-custody `
  --move-to dryrun/d4/custody
```

完整脚本与输出位于未跟踪实验目录 `dryrun/d4/`：`seal_capture_probe.py`、
`seal_addendum_probe.py`、`probe-output.txt`、`addendum-output.txt`、
`d4-results.json`、`d4-addendum-results.json`。

---

## 7. 边界声明

- 本报告只测量**密封工具的覆盖面与检出能力**，不涉及任何模型行为或效果。
- 「拍不到」指**不在清单内**，不等于「不存在」；H6 尤其说明封签与来源绑定是两件事。
- 未改动 `seal_run.py`（红区文件），全部为只读调用。
