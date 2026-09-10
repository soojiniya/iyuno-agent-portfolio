import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ask_ai(instructions, user_input):
    response = client.responses.create(
        model="gpt-5.6",
        instructions=instructions,
        input=user_input,
    )
    return response.output_text


def run_agent(task):
    print("\n[1] 요청 분석 중...")

    analysis = ask_ai(
        """
        You are a task analysis agent.
        Analyze the user's request and identify:
        1. The main goal
        2. Important requirements
        3. A short execution plan
        Keep the response concise.
        """,
        task,
    )

    print("\n[2] 초안 생성 중...")

    draft = ask_ai(
        """
        You are an execution agent.
        Complete the user's task based on the analysis provided.
        Produce a useful and professional result.
        """,
        f"""
        User request:
        {task}

        Task analysis:
        {analysis}
        """,
    )

    print("\n[3] 결과 검토 중...")

    final_result = ask_ai(
        """
        You are a quality review agent.
        Review the draft for accuracy, clarity, and completeness.
        Fix any problems and return only the improved final answer.
        """,
        f"""
        Original request:
        {task}

        Draft:
        {draft}
        """,
    )

    return final_result


if __name__ == "__main__":
    print("=== IYUNO Agent Portfolio ===")

    user_task = input("\n처리할 작업을 입력하세요: ")

    result = run_agent(user_task)

    print("\n=== 최종 결과 ===")
    print(result)