import os
import json
import time
from github import Github
from openai import OpenAI
from tools import get_tools_schema, execute_tool, git_diff
from memory import load_memory, save_memory

MAX_STEPS = 25

def get_task_context():
    """Extracts task and repository context from the GitHub Actions environment."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    with open(event_path, "r") as f:
        event_data = json.load(f)
    
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    
    task = ""
    issue_number = None
    
    if event_name == "workflow_dispatch":
        task = event_data.get("inputs", {}).get("task", "")
    elif event_name == "issue_comment":
        task = event_data.get("comment", {}).get("body", "").replace("/agent", "").strip()
        issue_number = event_data.get("issue", {}).get("number")
        
    return repo_name, issue_number, task

def main():
    api_key = os.environ.get("AGENT_API_KEY")
    model = os.environ.get("AGENT_MODEL")
    gh_token = os.environ.get("GITHUB_TOKEN")
    
    if not all([api_key, model, gh_token]):
        raise ValueError("Missing AGENT_API_KEY, AGENT_MODEL, or GITHUB_TOKEN.")

    client = OpenAI(api_key=api_key)
    repo_name, issue_number, task = get_task_context()
    
    if not task:
        print("No task provided. Exiting.")
        return

    # Initialize state
    memory = load_memory()
    with open("AGENT.md", "r") as f:
        system_prompt = f.read()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Previous memory state: {json.dumps(memory)}\n\nCurrent task: {task}"}
    ]

    print(f"Starting agent loop for task: {task}")
    
    # Agent Action Loop
    for step in range(MAX_STEPS):
        print(f"--- Step {step + 1}/{MAX_STEPS} ---")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=get_tools_schema(),
            tool_choice="auto",
            temperature=0.2
        )
        
        message = response.choices[0].message
        messages.append(message)
        
        if not message.tool_calls:
            print("Agent finished task without further tool calls.")
            break
            
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            print(f"Calling tool: {function_name} with {arguments}")
            try:
                result = execute_tool(function_name, arguments)
            except Exception as e:
                result = f"Error executing {function_name}: {str(e)}"
                
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": str(result)
            })

        # Brief pause to avoid aggressive API rate limiting
        time.sleep(1)

    else:
        messages.append({
            "role": "user",
            "content": "You have reached the maximum of 25 steps. Please wrap up and provide a final report."
        })
        final_response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        messages.append(final_response.choices[0].message)

    # Reflection pass: before saving state and reporting, the agent reviews its
    # own work once, like a strict senior reviewer. Any failure here must never
    # crash the run — fall back to the plain report.
    final_state = messages[-1].content if messages[-1].content else "Task completed, but no final text was generated."
    report_content = final_state
    try:
        print("--- Reflection pass ---")
        try:
            diff_text = git_diff()
        except Exception as e:
            diff_text = f"(git_diff unavailable: {e})"
        reflection = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are the same agent, now reviewing your own work like a strict senior reviewer."},
                {"role": "user", "content": (
                    f"Original task: {task}\n\n"
                    f"Your final state / report:\n{final_state}\n\n"
                    f"Actual working-tree changes (git_diff):\n{diff_text}\n\n"
                    "List: (1) what was actually accomplished vs the task, "
                    "(2) anything unverified or risky, "
                    "(3) what the manager should check first."
                )}
            ],
            temperature=0.2
        )
        reflection_text = reflection.choices[0].message.content
        if reflection_text:
            report_content = f"{final_state}\n\n### 🔍 Self-Review\n\n{reflection_text}"
    except Exception as e:
        print(f"Reflection pass failed, reporting without it: {e}")

    # Save final state for next run
    save_memory({"last_task": task, "status": "completed", "steps_taken": step + 1})

    # Post report

    gh = Github(gh_token)
    repo = gh.get_repo(repo_name)
    
    if issue_number:
        issue = repo.get_issue(number=issue_number)
        issue.create_comment(f"🤖 **Agent Report:**\n\n{report_content}")
        print("Report posted to issue.")
    else:
        print(f"Workflow dispatch complete. Agent Report:\n{report_content}")

if __name__ == "__main__":
    main()
