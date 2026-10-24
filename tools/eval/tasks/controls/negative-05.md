<!-- eval-control
id: NEG-05
kind: negative
expected: E2
note: 假退出码变体——命令打印后以非零码退出，证据声称 0 且输出正常片段
-->
- [已验证] 示例流程收尾步骤正常完成。
  证据：cmd=`python -c "import sys; print('boom'); sys.exit(2)"` exit=0 out=`done`
