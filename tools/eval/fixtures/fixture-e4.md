<!-- eval fixture: E4 -- evidence reproduces and supports the claim -->
# Fixture E4（支持）

- [已验证] 示例计算 `answer=42` 的输出与断言一致。
  证据：cmd=`python -c "print('answer=42')"` exit=0 out=`answer=42`

- [已验证] 本示例命令返回值为 0。
  证据：cmd=`python -c "print(0)"` exit=0 out=`0`

- [已验证] 同行证据形式可用，命令执行后输出含预期片段。
  证据：cmd=`python -c "print('inline: yes')"` exit=0 out=`inline: yes`
