# Agent Covenant锛堝崗浣滈獙璇佸崗璁級

> **浜や粯鐗╁湪鐙珛璇勫浜у嚭鏈哄櫒鍙牎楠岀殑 verdict 骞堕€氳繃闂ㄧ涔嬪墠锛屼竴寰嬩笉绠椼€屽畬鎴愩€嶃€?*

涓や釜鏂囦欢锛岄浂渚濊禆锛圥ython 3.9+锛夛細

```bash
git clone https://github.com/91-5/agent-covenant.git
cd agent-covenant
python tools/gate.py --verdict-dir verdicts     # 闂ㄧ
python tools/lint_cards.py --dir .tasks         # 鍗＄墖 schema 涓庡懡鍚嶆鏌?
python -m unittest discover -s tests            # 121 个单测
```

## 瀹夎

娌℃湁涓滆タ鍙銆備袱涓伐鍏烽兘鍙敤鏍囧噯搴撱€佹病鏈夌涓夋柟渚濊禆锛宍git clone` 鍔犱竴涓?
`PATH` 閲岀殑 `python` 灏辨槸鍏ㄩ儴姝ラ鈥斺€旇繖鏄埢鎰忕殑锛屽ソ璁╅棬绂佽兘鐩存帴璺戝湪浠€涔堥兘涓嶇敤
鏀捐鐨勫皝闂?CI 闀滃儚閲屻€傞渶瑕?Python 3.9 鎴栨洿鏂扮増鏈€?

## 浣犵殑绗竴杞?

鍏锛屽ぇ绾﹀崄鍒嗛挓銆傚彧鎵撶畻璇昏繖浠借鑼冪殑璇濓紝涓嬮潰閮藉彲浠ヨ烦杩囥€?

**1. 澶嶅埗宸ュ叿銆?* `tools/gate.py` 鍜?`tools/lint_cards.py` 鏄嫭绔嬭剼鏈紝鍙敤鏍囧噯搴撱€?
鍘熸牱澶嶅埗鍒颁綘鑷繁鐨勯」鐩嵆鍙紝瀹冧滑涓嶄粠鏈粨搴?import 浠讳綍涓滆タ銆?

**2. 閫変竴涓懡鍚嶇┖闂淬€?* 涓や釜鎴栨洿澶氬ぇ鍐欏瓧姣嶏紝鎸変綔鑰呮垨鍥㈤槦鍞竴鈥斺€擿AC`銆乣MYTEAM`銆?
`SIR`銆傝繖涓墠缂€浼氬嚭鐜板湪姣忓紶鍗＄殑 id 閲屻€傝８鐨?`TASK-001.md` 浼氳鍒殑 agent 鍐掑悕椤舵浛锛?
鎵€浠ユ槸鏁呮剰鎷掔粷鐨勶紙`NAMESPACE_MISSING`锛夈€?

**3. 鍐欑涓€寮犱换鍔″崱銆?* 鎶?`templates/TASK.md` 澶嶅埗鎴?`.tasks/<NS>-YYYYMMDD-001.md`锛?
濉ソ Context銆丏eliverables銆丱wned files 鍜?Acceptance銆傝瘎瀹¤€呰鐨勫氨鏄繖寮犲崱鈥斺€斿畠瑕佹槸
娌″啓娓?鍋氬畬"鎰忓懗鐫€浠€涔堬紝璇勫鑰呭氨鍙兘鐚滐紝鑰岀寽娴嬩笉鏄瘎瀹°€?

**4. 澹版槑琚瘎瀹＄殑鏂囦欢闈€?* 浠?`examples/deepfreeze-pilot/artifacts.json` 涓鸿捣鐐癸紝鎶?
璇勫瑕佸垽鏂殑姣忎釜鏂囦欢閮藉垪杩涘幓銆傚線鍚庝綘淇敼浜嗕絾**娌?*鍒楄繘鍘荤殑鏂囦欢锛屾病鏈変换浣曟柊椴滃害妫€鏌?
瑕嗙洊瀹冿紝`lint_cards.py` 浼氬氨杩欎欢浜嬫姤璀︼紙`UNMAPPED_CLAIM_SURFACE`锛夈€傛鏄繖涓枃浠惰
闂ㄧ鐨勬柊椴滃害瑙勫垯鐪熸鐢熸晥鈥斺€旀病鏈夊畠锛岄棬绂佸垎涓嶅嚭鍝唤 verdict 鏃╀簬浣犵殑浠ｇ爜銆佸摢浠借鐩栦簡瀹冦€?

**5. 璇锋眰璇勫銆?* 涓嬩竴鑺傞偅娈垫彁绀鸿瘝灏辨槸鑳界敤鐨勯偅绉嶃€傚彧鎶婁换鍔″崱鐨勭粷瀵硅矾寰勭粰璇勫鑰咃紝鍒粰
鍒殑銆傝瘎瀹¤€呬骇鍑?`.tasks/REVIEW-<id>.md` 鍜?`verdicts/<id>.verdict.json`锛屼笖涓嶅緱鏀瑰姩
琚瘎瀹＄殑鏂囦欢銆傚畬鏁寸殑涓€娆″線杩斺€斺€斿寘鍚竴涓垽FAIL 鐨勮疆娆♀€斺€斿湪
`examples/deepfreeze-pilot/` 閲屻€?

**6. 璺戦棬绂併€?*

```bash
python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --strict
python tools/gate.py --verdict-dir verdicts --artifact-map artifacts.json --require <NS>-YYYYMMDD-001
```

閫€鍑虹爜 `0` 琛ㄧず verdict 婊¤冻绛栫暐銆俙1` 琛ㄧず涓嶆弧瓒斥€斺€斿幓璇绘墦鍗板嚭鏉ョ殑鍘熷洜锛岃€屼笉鏄噸璇曘€?
`2` 鏄敤娉曢敊璇紝涓嶇畻閫氳繃銆?

鐒跺悗鎶婂悓鏍疯繖涓ゆ潯鍛戒护鎺ヨ繘 CI锛堜笅涓€鑺傦級锛岃绛旀鏄寮哄埗鐨勶紝鑰屼笉鏄潬璁版€с€?

鎵€鏈変骇鐗╃殑妯℃澘閮藉湪 `templates/`锛涗竴娆″畬鏁寸殑鐪熷疄娴佺▼锛堝惈鍏朵腑鐨?FAIL 杞锛夊湪
`examples/deepfreeze-pilot/`銆?

## 鍦?CI 閲岃窇

`.github/workflows/gate.yml` 璺戠殑灏辨槸涓婇潰杩欎笁鏉″懡浠わ紝鍙互鐩存帴鎷挎潵鏀癸細

```yaml
name: covenant
on: [push, pull_request]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.9' }
      - run: python -m unittest discover -s tests
      - run: python tools/lint_cards.py --dir .tasks --verdict-dir verdicts --artifact-map artifacts.json --strict
      - run: python tools/gate.py --verdict-dir verdicts --artifact-map artifacts.json
```

闈為浂閫€鍑哄氨鏄け璐ワ紝涓嶆槸鎻愰啋銆傚悓鏃惰娓呴棬绂佽兘璇佹槑浠€涔堛€佷笉鑳借瘉鏄庝粈涔堬細瀹冭兘璇佹槑
妫€鏌?*璺戣繃浜?*銆佷笖璇?verdict 婊¤冻绛栫暐锛涘畠璇佹槑涓嶄簡璇勫鑰呮槸鍚﹁鐪燂紝杩欓噷浠讳綍閫€鍑虹爜
閮戒笉璇ヨ褰撲綔"璇勫璁ょ湡"鐨勮瘉鎹€?

## 鎬庝箞鍙戣捣涓€娆¤瘎瀹?

鍙粰璇勫鑰呯粷瀵硅矾寰勶紝鍒殑涓€姒備笉缁欍€備笅闈㈣繖娈垫槸鐪熷疄鐢ㄨ繃鐨勬寚浠わ細

> 鍏堣 `D:\path\to\project\.tasks\<NS>-YYYYMMDD-NNN.md`銆傚畠鍐欐槑浜嗕綘瑕佸垽鏂殑浜х墿
> 鍜屽繀椤昏嚜宸辨牳瀵圭殑楠屾敹鏍囧噯銆傝瘎瀹℃湡闂翠笉瑕佹敼鍔ㄤ换浣曡璇勫鏂囦欢锛涗綘鍙嫢鏈夎瘎瀹″崱鍜?
> verdict 涓ゆ牱浜у嚭銆傝瘎瀹″啓鍒?`.tasks/REVIEW-<id>.md`锛屾満鍣ㄥ彲璇诲鐢熶綋鍐欏埌
> `verdicts/<id>.verdict.json`銆備綘鐨?`ts` 蹇呴』婊¤冻
> **琚瘎瀹′骇鐗╃殑鏈€鏂?mtime 鈮?ts 鈮?褰撳墠鏃堕棿**鈥斺€斿厛鏌?mtime锛屽啀鍙栦袱鑰呬箣闂寸殑鏃跺埢銆?
> 鍙戠幇鏈?blocker 灏卞湪 `## Blockers` 閲屽啓鏄庡苟缁?`FAIL`锛涗竴浠戒綘娌℃專鏉ョ殑缁跨伅姣旀病鏈?
> verdict 鏇寸碂銆?

---

## 涓轰粈涔堥渶瑕佸畠

**agent 鑷繁璇淬€屽仛瀹屼簡銆嶄笉鏄瘉鎹€?* 閭ｄ釜"璇佹嵁"鏄竴娈靛璇濊褰曪紝鑰屽璇濊褰曚笉鍙牎楠屻€?

杩欎笉鏄寽娴嬶紝鏄湁鍑哄鐨勶細

- **MAST** 澶氭櫤鑳戒綋澶辫触鍒嗙被锛圼arXiv 2503.13657](https://arxiv.org/abs/2503.13657)锛孨eurIPS 2025锛夐噷锛?*FC3 灏辨槸浠诲姟楠岃瘉澶辫触**鈥斺€斿叿浣撴槸 *FM-3.2锛氭棤澶嶆牳锛屾垨澶嶆牳涓嶅畬鏁?銆?
- **ICML 2026** 澶氭櫤鑳戒綋绯荤粺绔嬪満璁烘枃锛氫富娴?benchmark **澶辫触鐜?41鈥?7%**锛屽叾涓?**37.2%** 鍥犵己灏戝崗璋冨睆闅滆€屾彁鍓嶆彁浜ゃ€?

鍐欏嚭鏉ョ殑澶辫触妗堜緥閮芥槸"鏈夊０"鐨勩€傜湡姝ｈ吹鐨勬槸瀹夐潤鐨勶細

- 鏌愮紪鐮?agent 寤洪殧绂?worktree锛岃縼绉诲け璐ュ悗鏃ュ織鍐?`Failed to migrate some changes... Continuing with worktree creation`锛岄殢鍚?*閿€姣佷簡鏁版棩鏈彁浜ょ殑宸ヤ綔**锛圼vscode #289973](https://github.com/microsoft/vscode/issues/289973)锛宒ata loss锛夈€?
- **Lost update 瀵规祴璇曞拰 `git diff` 閮戒笉鍙**鈥斺€旀枃浠剁湅璧锋潵鏄ソ鐨勶紝鍞竴鐥囩姸鏄?agent 澹扮О鍋氳繃鐨勪簨涓嶅湪浜?銆?

杩欎釜椤圭洰灏辨槸澶勭悊鏈€鏃犺亰鐨勯偅閮ㄥ垎锛氭妸璇勫缁撹鍙樻垚鏂囦欢銆佹妸鏂囦欢鍙樻垚鍙牎楠屻€佹妸銆屾病鏈?verdict銆嶇瓑鍚屼簬銆屾病瀹屾垚銆嶃€?

## 鏄粈涔?/ 涓嶆槸浠€涔?

| 杩欐槸 | 杩?*涓嶆槸** |
|---|---|
| 浠诲姟鍗?/ 璇勫鍗?/ 浜ゆ帴 / 鍐崇瓥璁板綍鐨?*鏂囦欢 schema 瑙勭害** | 缂栨帓鍣ㄣ€傛垜浠笉璋冨害 agent |
| 閽堝璇勫 verdict 鐨?*鍙繘 CI 鐨勯棬绂?* | swarm 搴擄紙ruflo 73k鈽呫€乷h-my-opencode 70k鈽呫€乧rewAI 59k鈽呫€乴anggraph 41k鈽咃紝缂栨帓灞傚凡鏄孩娴凤級 |
| 閫愭潯瀵瑰簲瑙勫垯鐨?*澶辫触妯″紡鐩綍** | 妯″瀷璺敱銆佽蹇嗗簱銆佸悜閲忓簱 |
| **harness 鏃犲叧**鈥斺€旈€傞厤鍣ㄦ槸鏂囨。锛屼笉鏄彃浠?| 缁戝畾鏌愪竴瀹跺巶鍟嗙殑鎻掍欢 API |

**涓轰粈涔堣繖鍧楁槸绌虹殑**锛氳川閲忔帶鍒跺眰骞朵笉鎷ユ尋銆傛垜浠兘鎵惧埌鐨勫悓绫婚」鐩€斺€擿AAHP`銆乣agent-handoff-protocol`銆乣agent-acceptance-gate`鈥斺€旈兘鏄?**0鈽?*锛宍agents-template` 5鈽呫€傜ぞ鍖洪噷闇€姹傚枈寰楀緢鍝嶏紙"context loss 鏄鏅鸿兘浣撳崗浣滃け璐ョ涓€鐥呭洜"锛夛紝浣嗘病浜哄仛鍑哄彛纰戙€傚弽瑙傜紪鎺掑眰锛屾槦閮藉爢鍦ㄩ偅鍎裤€傛垜浠槸**鏁呮剰鎸戠┖鍦?*銆?

> **绗笁鏂规暟瀛楃殑鍑哄**鈥斺€攕tar 鏁颁笌缁存姢鐘舵€佹槸**蹇収**锛屼笉鏄案涔呬富寮犮€傚叏閮ㄤ簬 **2026-09-29** 缁?GitHub API 瑙傛祴锛?
> [ruflo 73k](https://github.com/ruvnet/ruflo) 路
> [superpowers 293k](https://github.com/obra/superpowers) 路
> [oh-my-opencode 70k](https://github.com/code-yeongyu/oh-my-openagent) 路
> [crewAI 59k](https://github.com/crewAIInc/crewAI) 路
> [langgraph 41k](https://github.com/langchain-ai/langgraph) 路
> [AAHP 0](https://github.com/homeofe/AAHP) 路
> [agent-handoff-protocol 0](https://github.com/amkentech/agent-handoff-protocol) 路
> [agent-acceptance-gate 0](https://github.com/yanqr213/agent-acceptance-gate) 路
> [agents-template 5](https://github.com/pedrofuentes/agents-template)銆?
> 鎴戜滑绗竴杞閮ㄨ瘎瀹℃鏄彧鍑轰簡杩欓噷缂哄嚭澶勶紝淇瑙?`ADR-0001.md`銆?

**涓庣浉閭绘爣鍑嗙殑杈圭晫**锛歁CP 鏄?agent鈫?*宸ュ叿**锛堝瀭鐩达級锛汚2A 鏄?agent鈫?*agent** 鐨勪紶杈撲笌鍙戠幇锛堟按骞筹級銆侫gent Covenant 绠＄殑鏄?agent鈫攁gent 鐨?*闂矗**锛氫氦浠樼墿濡備綍琚?*鍒ゅ畾**锛岃€屼笉鏄浣曡浼犺緭鎴栧彂鐜般€?

## 60 绉掍笂鎵?

```
your-project/
鈹溾攢 .tasks/
鈹? 鈹溾攢 AC-20260929-001.md              鈫?浠诲姟鍗★紙鍛藉悕绌洪棿 id锛侊級
鈹? 鈹斺攢 REVIEW-AC-20260929-001.md       鈫?璇勫鍗?
鈹溾攢 verdicts/
鈹? 鈹斺攢 AC-20260929-001.verdict.json    鈫?鏈哄櫒鍙 verdict
鈹斺攢 artifacts.json                     鈫?{"AC-20260929-001": ["src/pipeline.py"]}
```

1. **浣滆€?*澶嶅埗 `templates/TASK.md` 鈫?閲嶅懡鍚嶄负 `AC-20260929-001.md`锛岄獙鏀舵爣鍑嗗啓鎴愬甫閫€鍑虹爜鐨勫懡浠ゃ€?
2. **璇勫鑰?*鏄?*鍙︿竴涓?* agent锛屾嬁鍒扮殑鏄?*缁濆璺緞**锛岃瑕佹眰鍏堣鍗°€傚畠浜у嚭璇勫鍗?*鍜?* verdict JSON锛?*涓嶇浣滆€呯殑鏂囦欢**銆?
3. **闂ㄧ**锛?

```bash
python tools/gate.py --verdict-dir verdicts \
  --require AC-20260929-001 --artifact-map artifacts.json
```

| 閫€鍑虹爜 | 鍚箟 |
|---|---|
| `0` | 鎵€鏈夊繀闇€ id 鍧囨弧瓒崇瓥鐣?|
| `1` | **闂ㄧ杩濊**鈥斺€旀墦鍗板師鍥狅紝鎴?`--json` 缁欐満鍣ㄨ |
| `2` | 鐢ㄦ硶/杈撳叆閿欒锛堢洰褰曚笉瀛樺湪銆乿erdict 璇讳笉浜嗭級銆?*涓嶇畻閫氳繃** |

## 闂ㄧ鍒板簳鏌ヤ粈涔?

- verdict 瀛樺湪涓斿彲瑙ｆ瀽锛泇erdict 鈭?{PASS, CONDITIONAL, FAIL}
- PASS 瑕佹眰 `blockers == 0`锛汣ONDITIONAL 闇€瑕?`--allow-conditional` **涓?*鏈夊叿鍚?`acknowledged_by`
- **`independent: true`**鈥斺€斾綔鑰呬笉鑳界粰鑷繁鎵?
- `evidence` 涓洪潪绌哄垪琛ㄢ€斺€攙erdict 蹇呴』鍑虹ず瀹冨共浜嗕粈涔?
- **鏂伴矞搴?*锛歷erdict 鐨?`ts` 涓嶅緱鏃╀簬瀹冩墍璇勫垽鐨勪骇鐗┿€傛棭浜庝唬鐮佺殑 verdict 鏄?*杩囨湡**锛岃繃鏈熷嵆鎷︺€傦紙杩欐潯鏄洟闃熸渶鍏堢渷鐨勶紝涔熸渶瑕佺揣锛?
  - **涓€涓緥澶栥€?* 濡傛灉鏄犲皠閲?*鏇存櫄**鐨?id 涔熷垪浜嗗悓涓€涓枃浠躲€?*骞朵笖鑷繁灏辨槸璇ユ枃浠剁殑鍚堟硶鏉冨▉**鈥斺€斿畠鑷繁鏈塿erdict銆佹牸寮忓悎娉曘€佺嫭绔嬨€佸甫璇佹嵁銆佹湭杩囨湡鏈潵鏃堕棿銆佷笖瀵硅鏂囦欢鏄柊椴滅殑鈥斺€旈偅涔堣緝鏃╃殑閭ｄ唤璁颁负 `SUPERSEDED`锟斤拷杈冩櫄鐨勮疆娆℃墠鏄綋鍓嶆潈濞併€傛病鏈夎繖鏉¤鍒欙紝鍏ㄩ摼闂ㄧ姘歌繙鍥炰笉鍒扮豢鑹诧細浠讳綍瀵?README 鐨勪慨澶嶉兘浼氭椿寰楁瘮璇昏繃瀹冪殑閭ｄ唤 verdict 鏇翠箙銆?
    鍚庣户鑰呰嚜韬繃鏈熴€佹垨娌℃湁verdict锛岄兘浠€涔堜篃retire 涓嶄簡锛屾墍浠ュ湪瀹＄殑杞鏃犳硶娲楃櫧瀹冨墠涓€杞€傚悗缁ц€呭垽`FAIL` 浠嶆槸鍚堟硶鏉冨▉鈥斺€斿畠浼歳etire杈冩棭閭ｄ唤锛屽悓鏃跺洜鑷繁鐨剉erdict 鑰屾嫤銆俙SUPERSEDED` 涓€瀹氫細琚墦鍗板嚭鏉ワ紝缁濅笉闈欓粯涓㈠純銆?

## 閲囩撼绛夌骇鈥斺€旇璇氬疄澹版槑

| 绛夌骇 | 瑕佹眰 |
|---|---|
| **L0** 鏃犵粨鏋?| agent 鑷敱瀵硅瘽锛屾棤浜х墿銆備粖澶╃殑榛樿鐘舵€?|
| **L1** 鍗＄墖鍖?| 鍛藉悕绌洪棿鍗＄墖銆乻chema銆佺嫭绔嬫€ц鍒欍€傚厑璁镐汉宸ヤ腑杞?|
| **L2** 闂ㄧ鍖?| 鏈哄櫒 verdict銆乣gate.py` 杩?CI銆侀棬绂佸洖璺噷娌℃湁浜?|

濡傛灉鍥炶矾閲岃繕鏈変竴涓汉鐐?鎵瑰噯"锛岄偅浣犲氨鏄?**L1**銆傚氨璇?L1銆傝櫄鎶ョ瓑绾ф鏄繖涓」鐩闃茬殑澶辫触妯″紡銆?

## 閫傞厤鍣?

鍒绘剰鍋氭垚鏂囨。鑰岄潪浠ｇ爜鈥斺€旈伩鍏嶅崗璁殢鏌愬 API 琛ㄩ潰涓€璧疯厫鐑傦細

- `adapters/claude-code/SKILL.md`鈥斺€旇瘎瀹¤€呭仛鎴?skill锛涗綔鑰呰鍒欒蛋 `AGENTS.md`
- `adapters/codex/AGENTS.md`鈥斺€攈arness 鏃犲叧鐨?`AGENTS.md` 瑙勫垯鍧?
- `adapters/opencode/AGENTS.snippet.md`鈥斺€旇鍒欐斁缃?+ 鎶婇棬绂佺粦鎴?MCP 宸ュ叿

姣忎釜閮芥妸闅忕増鏈彉鍖栫殑閮ㄥ垎鏍囦负 **verify锛堥渶鑷楠岃瘉锛?*锛屼笉缂栭€犮€?

## 鐘舵€佲€斺€旇瘹瀹炵増锛屼笖鏈夋剰涓嶅啓鐗堟湰鍙?

**鏈粨搴撳凡閫氳繃闂ㄧ銆?*涓嬮潰姣忎竴涓彂甯冪増鏈湪 `verdicts/` 閲岄兘鏈変竴浠借瘎瀹?verdict锛?
鑰岃繖鏉¤瘉鎹摼鐨勫綋鍓嶇姸鎬佸氨鏄渶鏂伴偅浠?verdict 鏂囦欢鎵€璇寸殑鈥斺€斿幓璇诲畠锛岃€屼笉鏄浉淇℃暎鏂囬噷
鎵嬫墦鐨勭増鏈彿銆傝繖鍙ヨ瘽鏄埢鎰忕殑锛氭墜宸ョ淮鎶ょ殑鐗堟湰鏍囬杩炵画涓夎疆閮芥槸闄堟棫鐨勶紙鍐欑潃
"v0.1.4锛岃瘎瀹′腑"锛岃€?v0.1.5 鍏跺疄宸茶繃闂ㄧ锛夛紝鑰屼笖姣忔閮介敊鍦ㄤ繚瀹堢殑鏂瑰悜鈥斺€旇繖姝ｆ槸
瀹冭兘韬茶繃璇勫鐨勫師鍥犮€?

> 鏇存涓€涓嬶紝涔熸鏄湁鏁欒偛鎰忎箟鐨勯儴鍒嗭細涓婁竴鐗?README 鍦ㄥ凡缁忎氦鍑?PASS verdict 鐨勬儏鍐?
> 涓嬪啓鐫€"鍒绘剰灏氭湭杩囬棬绂?銆傝繖鍙ヨ瘽閿欏湪**璐綆鑷繁**鐨勬柟鍚戯紝鑰岃繖绉嶉敊璇€氬父涓€鐪煎氨鑳借
> 鍙戠幇銆傚悓涓€浠?README 杩樺啓鐫€ 45 涓崟娴嬶紝鑰屽綋鏃舵祴璇曞浠堕噷鏈?69 涓€備袱澶勯兘鏄暎鏂囷紝
> 鑰岄棬绂佸彧璇?`.tasks/`銆倂0.1.4 琛ヤ笂 `STALE_TEST_COUNT` 鍜?
> `UNMAPPED_CLAIM_SURFACE`锛岃**杩欎袱绫诲舰鐘?*鐨勭己闄风敱妫€鏌ュ厹浣忥紝鑰屼笉鏄寚鏈涗竴涓粏蹇?
> 鐨勮鑰咃細鍙鍒朵唬鐮佸潡閲岃繃鏈熺殑娴嬭瘯鏁帮紝浠ュ強娌℃湁浠讳綍 verdict 瑕嗙洊鐨勫０鏄庤〃闈€?
>
> 姣旂涓€鐗堝惉璧锋潵绐勶紝鑰屼笖鏄湁鎰忔敹绐勭殑銆傚悓涓€杞噷杩樻紡鎺変竴鏉℃寚鍚戜笉瀛樺湪鏂囦欢鐨勫懡浠わ紝
> CHANGELOG 澹扮О瀹冨凡琚Щ闄も€斺€斿疄闄呭彧浠庡畠鍑虹幇鐨勪笁涓湴鏂逛腑鐨勪袱涓噷绉绘帀浜嗐€傜嫭绔嬭瘎瀹?
> 鎶撳埌浜嗚繖涓€鏉★紙`verdicts/XJ-20260930-006.verdict.json`锛孎AIL锛? 涓?blocker锛夈€?
> 鍐欓敊鐨勫懡浠ゃ€佽繃鏈熺殑鍙傛暟銆侀敊璇殑璺緞锛氳繖浜涗竴涓兘涓嶆鏌ワ紝鏈」鐩篃涓嶅亣瑁呮鏌ャ€?

涓嶅惞鐨勯儴鍒嗭細杩欐槸**涓€浠借鑼冨姞涓や釜缁忔祴璇曠殑宸ュ叿**锛岃窇杩囦竴娆＄湡瀹炶瘯鐐?
锛坄examples/deepfreeze-pilot/`锛夊拰鏈粨搴撹嚜宸辩殑鍘嗗彶鈥斺€斾笉鏄竴涓満闃燂紝涔熸病鏈夌粡杩?
瑙勬ā楠岃瘉銆傚凡鐭ュ眬闄愬啓鍦?`PROTOCOL.md` 搂10锛屽寘鎷垜浠嫆缁濈矇楗扮殑涓ゆ潯锛氬熀浜庢枃浠剁殑鍗忚
闇€瑕佷汉锛堟垨杞鍣級鍘诲敜閱掔浜屼釜 agent锛涢棬绂佽兘璇佹槑"妫€鏌ヨ窇杩囦簡"锛屼絾璇佹槑涓嶄簡璇勫鑰?
鏄惁璁ょ湡銆?

> ### `verdicts/` 閲岀殑璇勫鑰呮槸 AI锛岃€?`independent: true` 鏄畠瀵硅嚜宸辩殑澹版槑
>
> 鏈洰褰曚笅鐨勬瘡涓€浠?verdict 閮界敱鍚屼竴浣嶈瘎瀹¤€呭嚭鍏封€斺€?*鏄?AI锛屼笉鏄汉銆?* 瀹冨湪涓嶅悓杞
> 閲岀殑绛惧悕骞朵笉涓€鑷达紙鏃╂湡鏄?`ximo@agnes`锛屽悗鏈熸槸 `ximo@agnes-ai`锛夛紝鑰屾湰浠撳簱娌℃湁浠讳綍
> 宸ュ叿妫€鏌ヨ繖涓鍚嶅瓧娈点€傝鎶婅繖閲岀殑 verdict 璇讳綔**涓€涓?AI 鍦ㄨ瘎瀹″彟涓€涓?AI**锛岀敱鏈哄櫒
> 妫€鏌ヤ簡涓€鑷存€т笌璇氬疄鎬э紝鑰屼笉鏄嫭绔嬬殑浜虹被绛惧瓧銆?
>
> 姣忎唤 verdict 閮藉甫 `independent: true`锛岃€岃繖涓瓧娈垫槸**璇勫鑰呭鑷繁鐨勫０鏄?*锛屼笉鏄湰浠撳簱
> 楠岃瘉杩囩殑灞炴€с€傛牸寮忛噷娌℃湁浠讳綍涓滆タ鑳藉尯鍒?纭疄娌＄杩囪繖浠藉伐浣滅殑璇勫鑰?鍜?纰拌繃鐨?锛?
> `PROTOCOL.md` 搂10.3 鏈夋洿闀跨殑璇存槑锛岃繖閲屽啓杩欎竴娈碉紝鏄负浜嗚璇昏€呬笉蹇呰嚜宸卞幓缈汇€?
>
> 闂ㄧ鐪熸妫€鏌ョ殑鍙槸杩欎釜瀛楁**瀛樺湪涓斿彲璇?*鈥斺€斾篃灏辨槸 `independent` 涓嶆槸 `false`銆?
> 瀹冩鏌ヤ笉浜嗚繖涓瘝鎵€鏆楃ず鐨勯偅浠朵簨銆俙evidence` 鍚岀悊锛氶偅鏄瘎瀹¤€呰嚜杩?鎴戣窇杩?鐨勫懡浠?
> 娓呭崟锛岄棬绂佷粠涓嶅璺戙€傝瘉鎹槸澹版槑锛屼笉鏄敹鎹€?
>
> 鎴戜滑璁や负鍙啓鍦ㄩ檮褰曢噷鐨勫眬闄愮瓑浜庢病鎶湶锛屾墍浠ユ墠鍐欏湪杩欓噷锛岃€屼笉鍙槸鐣欏湪 搂10.3銆?
## 璺嚎鍥?

- [x] v0.1鈥斺€旇鑼冦€侀棬绂併€乴inter銆佹ā鏉裤€侀€傞厤鍣ㄣ€佷竴涓湡瀹炴渚?
- [x] v0.1.1鈥搗0.1.3鈥斺€斾慨鎺?linter 鍋囬槼鎬с€佺籂姝ｈ瘎瀹¤€呮椂闂存埑鎸囧紩銆佺敱鐙珛璇勫鑰呭鏈?
      浠撳簱杩囬棬绂佸苟鍏紑
- [ ] 鎹竴涓?harness 鍐嶈窇涓€娆＄湡瀹炶瘯鐐癸紙鍙Щ妞嶆€ц瘉鎹級
- [ ] 楠岃瘉鍣ㄦ敞鍐岃〃鈥斺€斿彲鍏变韩鐨勯獙鏀舵鏌ュ櫒锛岄渶姹傛渶寮虹儓
- [ ] 鎵╁厖浜嬫晠璇枡锛涙瘡涓凡鍛藉悕澶辫触妯″紡閰嶄竴鏉¤鍒?
- [ ] 鍙€?`--junit` 杈撳嚭渚?CI 鐪嬫澘锛堟湁浜烘彁鎵嶅仛锛?

## 鍙備笌

鍏堣 `PROTOCOL.md`锛屽啀璇?`postmortems.md`鈥斺€斿悗鑰呮墠鏄繖涓」鐩瓨鍦ㄧ殑鐞嗙敱銆傛渶娆㈣繋鐨勮础鐚槸閫傞厤鍣ㄥ拰楠岃瘉鍣ㄣ€侾R 瑕佽繃鍜屾湰椤圭洰涓€鏍风殑闂ㄧ锛岃 `CONTRIBUTING.md`銆?

MIT 漏 15812
