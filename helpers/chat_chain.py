from typing import List, Optional, AsyncGenerator
# import langchain
# from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
# from langchain.chat_models import init_chat_model
# from langchain.tools import tool
# from langchain import hub
# from langchain.agents import create_react_agent, AgentExecutor
# from models.ai import AI_Config
from fastapi import Request
from asyncio import gather
import re
import httpx
import os
import json
# langchain.debug = False
SCRAPER_BASE_URL = os.getenv("SCRAPER_BASE_URL", "http://localhost:8000")
DEFAULT_SYSTEM_PROMPT = """
You are an AI assistant with both knowledge base access and general knowledge capabilities. Your responses must be in pure HTML format using Tailwind CSS classes.

Response Guidelines:
1. Knowledge Priority:
   - First try to answer using the provided context (but don't let it know like (Based on Provided Context))
   - If context is insufficient or irrelevant, use your general knowledge
   - If neither is available, use the fallback response

2. HTML Formatting Rules:
   - Always respond with complete, valid HTML fragments
   - Use minimal semantic HTML (p, ul, ol, h2-h4, table when appropriate)
   - Apply Tailwind classes for styling (e.g., "mb-4", "text-gray-700")
   - Never include Markdown, backticks, or code fences
   - Never mention your knowledge sources

3. Content Requirements:
   - Direct answers only - no disclaimers or source references
   - Concise but comprehensive information
   - Structured for readability (headings, lists, paragraphs)
   - Tables only for tabular data

4. Knowledge Fallback:
   <div class="prose max-w-none">
     <!-- Your general knowledge answer here -->
   </div>

Fallback (when completely unknown):
<div class="bg-yellow-50 p-4 rounded-lg">
  <p class="font-medium">Sorry, I couldn't find specific information about this.</p>
  <p>For specialized inquiries, please contact <a href="mailto:info@leafaidx.ai" class="text-blue-600 hover:underline">info@leafaidx.ai</a></p>
</div>

Example Structure:
<div class="space-y-4">
  <h2 class="text-xl font-bold mb-2">[Main Answer]</h2>
  <p class="text-gray-700">[Detailed explanation]</p>
  <ul class="list-disc pl-5 space-y-1">
    <li>[Key point 1]</li>
    <li>[Key point 2]</li>
  </ul>
</div>
"""

ROUTER_PROMPT = """
You are an AI router. Your job is to decide if a user question requires tool usage (like scraping a website or calling an external function), or if it can be answered directly with general knowledge.

If the question likely needs tools, respond with: TOOL  
If the question can be answered directly, respond with: CHAT

Question: {question}
Response:
"""


def strip_code_fences(text: str) -> str:
    """
    Call this when that 
    """

    # Remove ```html or ``` at start and ``` at end
    # Also remove any triple backticks anywhere just to be safe
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.IGNORECASE)  # opening fence
    text = re.sub(r"\n?```$", "", text)
    text = text.replace("```", "")  # remove any leftover fences inside
    return text

# async def ask_question(
#     request: Request,
#     question: str,
#     history: List[dict] = [],
#     disabled_files: List[str] = [],
#     user_id: Optional[str] = None
# ) -> AsyncGenerator[str, None]:
#     """Optimized question answering with reduced payload"""
#     try:
#         # Get AI config (single query)
#         api = await AI_Config.first().only('api_key', 'model_name', 'prompt')
#         if not api or not api.api_key or not api.model_name:
#             yield "Error: AI configuration incomplete."
#             return

        
#         # context = await similarity_search(request, [question], disabled_files)
#         context = "No relevant context found."
        

        # Initialize LLM with limits
        # llm = init_chat_model(
        #     model=api.model_name,
        #     streaming=True,
        #     temperature=0.3,
        #     # max_tokens= 500,  # Limit response size
        #     model_kwargs={
        #         "api_key": api.api_key,
        #     }
        # )



        # Build optimized message payload
        # messages = [
        #     SystemMessage(content=(api.prompt[:500] if api.prompt else DEFAULT_SYSTEM_PROMPT)),
        #     *[
        #         msg for h in history[-3:]  # Last 3 exchanges only
        #         for msg in (
        #             HumanMessage(content=h['question'][:300]) if h.get('question') else None,
        #             AIMessage(content=h['answer'][:300]) if h.get('answer') else None
        #         ) if msg
        #     ],
        #     HumanMessage(content=f"Q: {question[:200]}\nContext: {context[:1500]}")
        # ]

        # response = await llm.ainvoke(messages)
        # clean_content = strip_code_fences(response.content)
        # yield clean_content

        # use_tools = await should_use_tools(question, api)
        # if use_tools:
        #     response_text = await run_agent(api, question)
        # else:
        #     response = await llm.ainvoke(messages)
        #     response_text = response.content
        # clean_content = strip_code_fences(response_text)
        # yield clean_content
        
    #     yield "Chat functionality with langchain is currently disabled."

    # except Exception as e:
    #     yield f"Error: {str(e)[:200]}"