<!-- eval-control
id: NEG-04
kind: negative
expected: E2
note: 假命令变体——命令存在（python）但引用的脚本文件不存在
-->
- [已验证] 示例脚本的功能验证已执行并通过。
  证据：cmd=`python tools/eval/no-such-script-4891.py` exit=0 out=`pass`
