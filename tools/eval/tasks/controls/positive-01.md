<!-- eval-control
id: POS-01
kind: positive
expected: E4
note: 真实成立——命令、退出码、输出片段全部可复现且锚命中
-->
- [已验证] 示例计算 `answer=42` 的输出与断言一致。
  证据：cmd=`python -c "print('answer=42')"` exit=0 out=`answer=42`
