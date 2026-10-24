<!-- eval fixture: E2 -- complete evidence whose observation does not reproduce -->
# Fixture E2（不可复现）

- [已验证] 本示例断言声称自检命令以退出码 0 结束，但该命令实际退出码非零。
  证据：cmd=`python -c "raise SystemExit(3)"` exit=0 out=`ok`

- [已验证] 本示例断言引用的复核文件在本仓中不存在，观察无从复现。
  证据：ref=tools/eval/fixtures/does-not-exist-e2.md
