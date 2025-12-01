from openai import OpenAI
import logging
from string import Template

class OpenaiTranslator:
    def __init__(self, api_key:str):
        self.logger = logging.getLogger(name=self.__class__.__name__)
        # OpenAI Instance
        self.client = OpenAI(
            api_key=api_key,
            base_url=r"https://api.chatanywhere.tech/v1/"
        )

    def translate_text(self, reviewed, text):

        system_prompt = SYSTEM_PROMPT_TEMPLATE.substitute(
            REVIEWED=reviewed,
            GLOSSARY=GLOSSARY,
            ORIGINAL=text
        )

        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",  # You can use gpt-3.5-turbo, gpt-4, gpt-4o, etc.
            messages=[
                {"role": "user", "content": system_prompt},
            ],
            stream=False,
            temperature=0.2
        )

        translated = response.choices[0].message.content

        return translated.strip()    


GLOSSARY = """
property -> 性质
property-based testing -> 基于性质的测试
monkey event -> 随机事件
widget -> 控件
lark -> 飞书
"""

SYSTEM_PROMPT_TEMPLATE = Template("""
你是一位专业的中英技术文档翻译助手。

我将提供一个英文的 Markdown 文件，请你将其翻译为中文。

为了保持术语一致性和语言风格，请严格参考以下 review 过的中文版本：
```
$REVIEWED
```

术语表如下：
```               
$GLOSSARY
```

请遵守以下要求：
1. 遇到相同或相似句子时，优先使用上方的参考中文翻译，尽量不要进行润色或句式改动；
2. 保留原始 Markdown 格式（如标题、列表、代码块等）；
3. 专有词汇（如 Activity、Fragment、Intent 等）、论文、人名等请保留英文；
4. 若原文中无匹配内容，才进行自由翻译，但请保持语言风格与参考一致；
5. 直接返回 Markdown 正文，不要用代码块包裹。


请开始翻译：
```                                  
$ORIGINAL
```
""")