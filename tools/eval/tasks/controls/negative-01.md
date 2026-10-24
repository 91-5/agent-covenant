<!-- eval-control
id: NEG-01
kind: negative
expected: E2
note: 假命令——引用完全不存在的可执行命令，观察无法复现
-->
- [已验证] 示例环境完整性自检命令执行通过。
  证据：cmd=`no-such-command-eval-4891 --check` exit=0 out=`ok`
