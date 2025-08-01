import os

from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API"))


def create_assistant(assistant_name, instructions, tools=None, file_ids=None):
    assistant = client.beta.assistants.create(
        name=assistant_name,
        instructions=instructions,
        tools=tools or [],
        model="gpt-4o",
        temperature=0.7,
    )

    return assistant


def delete_assistant(assistant_id):
    return client.beta.assistants.delete(assistant_id)


def update_assistant(
    assistant_id, assistant_name, instructions, tools=None, file_ids=None
):
    return client.beta.assistants.update(
        assistant_id,
        name=assistant_name,
        instructions=instructions,
        tools=tools or [],
        model="gpt-4o",
        temperature=0.7,
    )


def assistant_list():
    return client.beta.assistants.list(order="desc", limit=1)


def get_assistant(assistant_id):
    return client.beta.assistants.retrieve(assistant_id)


def create_thread():
    return client.beta.threads.create()


def send_message(thread_id, content):
    return client.beta.threads.messages.create(thread_id, role="user", content=content)


def get_messages(thread_id):
    return client.beta.threads.messages.list(thread_id=thread_id)
