from openai import OpenAI
from tools import TOOLS, run_tool
import os

client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:8080/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "not-needed"),
)

MODEL = os.getenv("MODEL", "mlx-community/Qwen3.6-35B-A3B-4bit")
MAX_STEPS = 10

SYSTEM_PROMPT = (
    "You are a code security reviewer. Use the tools to explore the project, "
    "read the files, and then report the security problems you find. "
    "For each problem give: file, what is wrong, why it is risky, and how to fix it. "
    "Only report problems you actually saw in the code."
)


def review():
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Review the project for security problems."},
    ]

    for step in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, max_tokens=4000
        )
        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            return message.content

        for call in message.tool_calls:
            print(f"[step {step + 1}] {call.function.name}({call.function.arguments})")
            result = run_tool(call.function.name, call.function.arguments)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": result}
            )

    return "Stopped: too many steps."


print(review())