<!-- eval-control
id: POS-05
kind: positive
expected: E4
note: 真实成立——证据行使用更深层缩进，抽取器必须仍能绑定
-->
- [已验证] 示例断言使用了缩进更深的证据行，仍应正确绑定并判支持。
    证据：cmd=`python -c "print('deep: indent-ok')"` exit=0 out=`indent-ok`
