<!-- eval fixture: E3 -- evidence reproduces but does not support the claim -->
# Fixture E3（不支持）

- [已验证] 示例仓库共有 42 个测试文件。
  证据：cmd=`python -c "print('files: 7')"` exit=0 out=`files: 7`

（命令真实可复现、退出码与输出均如声称——但断言锚 42 与观察无关，
观察既不矛盾于一个真实命题也不支撑它：确定性规则下归 E3。）
