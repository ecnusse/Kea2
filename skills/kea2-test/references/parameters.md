# Parameter interview guide

Ask in the user's language. All defaults below require explicit acceptance. Query current
kea2_check_test_setup.tool_defaults and the run-tool description before using this guide.
The null options below inherit CLI/engine behavior; do not send the word “default” as a value.

| Parameter | Purpose and choices to explain | Default / applicability |
| --- | --- | --- |
| serial | Android device serial; present discovered candidates and ask, even for one device | Required |
| packages | Target installed package IDs; one or several; confirm all targets | Required |
| running_minutes | Planned duration in minutes, positive integer | 10 |
| output_dir | Output parent on the MCP server; an experiment subdirectory is created inside | null → output under server working directory |
| property_path | Existing Python property file or directory, relative to server working directory or absolute | null → pure fuzzing; ask testing mode first |
| property_pattern | Python discovery filename glob in a directory | test*.py; ignored for a single file, not applicable for pure fuzzing |
| driver_name | Device attribute used by scripts, e.g. d means self.d | d; not applicable for pure fuzzing |
| max_step | Positive exploration-event limit; time/step bounds may end exploration when reached | null → no explicit finite event cap |
| throttle_ms | Nonnegative interval between events, milliseconds; affects operation frequency | null → engine default 200 ms |
| take_screenshots | Per-step screenshots, with storage/runtime costs; not the same as periodic capture | null → CLI false |
| profile_period | Positive event interval for periodic coverage profiling and screenshots | null → CLI 25 events |
| restart_app_period | Nonnegative event interval for app restart, 0 disables periodic restart | null → CLI 0 |
| act_whitelist_file | Device destination for Activity whitelist; contents come from project configs/awl.strings | null; only ask path if whitelist selected |
| act_blacklist_file | Device destination for Activity blacklist; contents come from project configs/abl.strings | null; mutually exclusive with whitelist |
| clear_app_data | Clear every target app before launch; irreversibly deletes login state, settings and local data | false; must explain before acceptance |

The current CLI/engine defaults above are documented values, not measurements. If installed
tool descriptions differ or a changed default cannot be established, ask for an explicit value
instead of promising the inherited value. No Activity restriction is an explicit choice covering
both list parameters. For non-applicable fields, record the reason and omit them from the call.
