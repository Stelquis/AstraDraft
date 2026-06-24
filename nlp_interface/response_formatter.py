from __future__ import annotations

from typing import List

from cad_understanding.models import Parameter
from nlp_interface.prompt_templates import (
    ANSWER_TEMPLATE,
    COMPARE_TEMPLATE,
    MULTI_ANSWER_TEMPLATE,
    NO_MATCH_TEMPLATE,
)


class ResponseFormatter:
    def format_single(self, param: Parameter) -> str:
        if param.value == 0 and param.unit == "" and param.raw_text:
            return f"- **{param.name}**: {param.raw_text}"
        return ANSWER_TEMPLATE.format(
            name=param.name,
            value=param.value,
            unit=param.unit,
        )

    def format_multiple(self, params: List[Parameter]) -> str:
        lines = []
        for p in params:
            if p.value == 0 and p.unit == "" and p.raw_text:
                lines.append(f"- **{p.name}**: {p.raw_text}")
            else:
                lines.append(f"- **{p.name}** = {p.value} {p.unit}")
        return MULTI_ANSWER_TEMPLATE.format(params_list="\n".join(lines))

    def format_all(self, params: List[Parameter]) -> str:
        if not params:
            return "当前图纸中未提取到任何参数。"
        return self.format_multiple(params)

    def format_compare(self, params_a: List[Parameter], params_b: List[Parameter]) -> str:
        lines = []
        for pa in params_a:
            for pb in params_b:
                diff = pa.value - pb.value
                cmp_word = "大于" if diff > 0 else "小于" if diff < 0 else "等于"
                lines.append(
                    f"- **{pa.name}** ({pa.value} {pa.unit}) {cmp_word} "
                    f"**{pb.name}** ({pb.value} {pb.unit})，差值 {abs(diff):.2f} {pa.unit}"
                )
        return COMPARE_TEMPLATE.format(compare_lines="\n".join(lines))

    def format_no_match(self, query: str, available: List[Parameter]) -> str:
        names = [f"  - {p.name}" for p in available[:20]]
        return NO_MATCH_TEMPLATE.format(
            query=query,
            available_params="\n".join(names) if names else "无",
        )
