<!-- eval fixture: E1 -- evidence lines present but field-incomplete -->
# Fixture E1（缺字段）

- [已验证] 本示例断言附了一行口头说明，但不含命令、退出码或 ref 字段。
  证据：相关背景在讨论中口头说明过，没有留下可复核记录。

- [已验证] 本示例断言给了命令却没给退出码或预期输出，仍属字段不完整。
  证据：cmd=`python -c "print('field-check')"`
