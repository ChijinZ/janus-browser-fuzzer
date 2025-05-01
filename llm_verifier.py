from enum import Enum
from typing import Dict, Optional
import json

from common import Transform
from openai import OpenAI
from dataclasses import dataclass, asdict
import logging


class ShouldChangeOrNot(str, Enum):
    ShouldChange = "ShouldChange"
    ShouldNotChange = "ShouldNotChange"
    NotSure = "NotSure"
    NoResponse = "NoResponse"


@dataclass
class LLMVerifiedResult:
    result: ShouldChangeOrNot
    reason: str

    def __init__(self, json_dict: Optional[Dict[str, str]]):
        try:
            assert json_dict is not None
            assert "shouldChange" in json_dict
            assert "reason" in json_dict

            self.reason: str = json_dict["reason"]

            match json_dict["shouldChange"]:
                case "True":
                    self.result = ShouldChangeOrNot.ShouldChange
                case "False":
                    self.result = ShouldChangeOrNot.ShouldNotChange
                case "NotSure":
                    self.result = ShouldChangeOrNot.NotSure
                case _:
                    self.result = ShouldChangeOrNot.NoResponse

        except AssertionError as e:
            self.result: ShouldChangeOrNot = ShouldChangeOrNot.NoResponse
            self.reason: str = f"{str(e)}"

    def to_dict(self):
        return asdict(self)


class LLMVerifier:
    def __init__(self):
        self.openai_api_key = "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"
        with open("llm_helper/system_prompt.txt", "r") as f:
            self.system_prompt = f.read()
        with open("llm_helper/css_desc.json", "r") as f:
            self.css_desc = json.load(f)

        print(self.system_prompt)

    def llm_verify(self, h1_path: str, h2_path: str, trans: Transform) -> LLMVerifiedResult:
        client = OpenAI(api_key=self.openai_api_key)

        with open(h1_path, "r") as f:
            h1_content = f.read()
        with open(h2_path, "r") as f:
            h2_content = f.read()

        if trans.prop not in self.css_desc:
            logging.error(f"{trans.prop} not in css_desc")
            return LLMVerifiedResult(None)

        prompt = f"HTML code before modification:\n```html\n{h1_content}\n```\n\n" \
                 f"HTML code after modification:\n```html\n{h2_content}\n```\n\n" \
                 f"Altered element type: {trans.el_type}. Altered css property: {trans.prop}. " \
                 f"css property value before modification: {trans.original_value}. " \
                 f"css property value after modification: {trans.new_value}\n" \
                 f"W3C standard description: {self.css_desc[trans.prop]}"

        print(prompt)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        content = response.choices[0].message.content
        print(content)
        json_dict = json.loads(content)
        llm_result = LLMVerifiedResult(json_dict)
        return llm_result
