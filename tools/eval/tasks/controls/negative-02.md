<!-- eval-control
id: NEG-02
kind: negative
expected: E2
note: 假退出码——命令真实存在但实际退出非零，证据声称退出 0
-->
- [已验证] 示例批处理的退出状态符合预期。
  证据：cmd=`python -c "raise SystemExit(3)"` exit=0 out=`ok`
