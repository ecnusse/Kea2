# Interaction examples

User: 我想用 Kea2 进行测试。

After read-only discovery:
“检测到设备 Pixel 6（序列号 …）。serial 用于选择执行测试的设备，是否使用它？
packages 用于指定目标应用。请提供包名；如果不清楚，我可以列出设备上的包名供你确认。”

Then ask testing mode and applicable script fields, duration/control, screenshots/profiling,
Activity restriction and output/data clearing. Explain each field before asking; do not dump
the raw tool schema on the user. Questions may be grouped, but every field must have a choice.

“running_minutes 控制计划测试分钟数，默认 10 分钟；希望用默认值还是指定时长？
max_step 限制探索事件数，默认不额外设上限；是否设定一个正整数上限？”

User: 测试 20 分钟，不限制步数，其他都默认。

Record duration=user_value and remaining applicable defaults=accepted_default; still resolve
any unknown required device/application identity. Never interpret silence as “other defaults”.

Final summary columns: parameter / selected value or inherited behavior / selection source.
Include non-applicable fields and reason. Clearly display clearing=false or the destructive
clearing=true choice, initialization writes, and output parent. Ask “确认按以上配置开始，并在
结束后自动分析本次结果吗？” Wait for an affirmative reply before mutations.

After launch, show its returned ID and continue polling yourself. Do not ask the user to enter
that ID or request result analysis again. If a later message changes settings before launch,
update the ledger, revalidate affected fields and show a revised confirmation.

When pure fuzzing returns status=running, phase=running and progress.executed=0, a suitable
update is: “任务状态为运行中。当前是纯自动探索，性质执行计数不代表探索步数；状态接口
没有提供实际探索步数，我会继续跟踪任务。” Do not say “测试步数为 0” or “测试没有启动”.
Only report a recorded exploration counter after obtaining it from MCP result tools, and identify
it as the latest available observation rather than a live measurement. If status and phase conflict,
explain the uncertainty instead of using this running-state example.
