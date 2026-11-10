"""
Large Language Model (LLM) client instance for the DataPilot agent.

Initializes an OpenAI-compatible Chat Model client reused across workflow nodes
and testing modules.
"""

from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config

# Initialize chat model from environment/config. Reuses client connection across graph nodes.
llm = init_chat_model(
    model=app_config.llm.model_name,
    # Any OpenAI-compatible provider (SiliconFlow, OpenAI, DeepSeek, Together, Groq, etc.)
    model_provider="openai",
    base_url=app_config.llm.base_url,
    api_key=app_config.llm.api_key,
    # Zero temperature for deterministic SQL generation and field extraction
    temperature=0,
)

if __name__ == "__main__":
    # Local validation probe for LLM connectivity
    print(llm.invoke("Hello, DataPilot").content)
