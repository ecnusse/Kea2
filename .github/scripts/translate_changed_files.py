import yaml
import os
import sys
from pathlib import Path
from gpt_translator import OpenaiTranslator


CONFIG_PATH = Path(".github/translation-list.yml")
OPENAI_API_KEY = os.getenv("API_KEY")


def translate_file(translator:OpenaiTranslator, reviewed_path: Path, input_path: Path, output_path: Path) -> None:
    """
    Translate a Markdown file and write the result to another file.
    """

    with open(reviewed_path, "r", encoding="utf-8") as f:
        reviewed_content = f.read()

    with open(input_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    # Translate content using OpenAI translator
    translated_content = translator.translate_text(reviewed_content,original_content)

    # Write translated content to output file
    with output_path.open("w", encoding="utf-8") as f:
        f.write(translated_content)


# locate output and reviewed path
def find_translation_entry(file_config_list, fname):
    for item in file_config_list:
        if item.get("path") == fname:
            return item["path_cn"], item["reviewed_cn"]


if __name__ == "__main__":
    files = []
    # argv[1] is the file list needed translation
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        files.extend(line.strip() for line in f.readlines() if line.strip())

    if len(files) == 0:
        exit(0)

    openai_translator = OpenaiTranslator(api_key=OPENAI_API_KEY)

    with open(CONFIG_PATH, "r") as f:
        file_config_list = list(yaml.safe_load(f))
    
    if "TRANSLATE ALL" in files:
        files = [item["path"] for item in file_config_list]
    
    translated = [] # output file list
    for fname in files:
        output, reviewed = find_translation_entry(file_config_list, fname)
        
        if output is None or reviewed is None:
            print(f"Cannot find translation entry for {fname}, skipped.")
            continue
        
        translate_file(
            translator=openai_translator,
            reviewed_path=Path(reviewed),
            input_path=Path(fname),
            output_path=Path(output)
        )
        translated.append(output)

    if translated:
        print("Translated files:")
        print("\n".join(translated))
