import yaml
import subprocess
from pathlib import Path

CONFIG_PATH = Path(".github/translation-list.yml")


# get changed file list in this commit
changed_files = set(subprocess.check_output(
    ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
    encoding="utf-8"
).splitlines())

to_translate = []
for f in changed_files:
    if (".github/scripts" in f) or (".github/workflows/markdown-translation-update.yml" in changed_files):
        to_translate = ["TRANSLATE ALL"]
        break

if not to_translate:
    with open(CONFIG_PATH, "r") as f:
        file_config_list = list(yaml.safe_load(f))
        for item in file_config_list:
            if item["path"] in changed_files or item["reviewed_cn"] in changed_files:
                to_translate.append(item["path"])

if to_translate:
    print("Files to be translated:")
    print("\n".join(to_translate))

with open("changed_files.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(to_translate))
