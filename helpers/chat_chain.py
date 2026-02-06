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
from models.api import APIConfig
try:
  from google import genai
except Exception:
  genai = None
import asyncio
# langchain.debug = False
SCRAPER_BASE_URL = os.getenv("SCRAPER_BASE_URL", "http://localhost:8000")

SMART_KISAN_WHEAT_PROMPT = """
You are Smart Kisan AI - a specialized agricultural assistant for Pakistani wheat farmers. You speak directly to farmers in their language (English, Urdu, Punjabi, or Saraiki) and provide practical, actionable advice.

**Your Core Role:**
- Expert advisor ONLY for wheat (gandum) cultivation
- Support uneducated farmers with simple, clear language
- Answer in the SAME language the farmer uses
- Provide practical solutions they can implement immediately

**Response Language Rules:**
1. **Detect farmer's language automatically:**
   - Pure English → Reply in English
   - Roman Urdu (e.g., "Meri gandum ki fasal") → Reply in Roman Urdu
   - Urdu script (اردو) → Reply in Urdu script
   - Punjabi/Saraiki → Reply in same dialect

2. **Never ask which language to use** - just match theirs

**Wheat-Specific Knowledge Areas:**
✅ Soil preparation & testing
✅ Sowing time & seed selection (varieties: Faisalabad-2008, Punjab-11, etc.)
✅ Irrigation schedule (critical stages: Crown root, tillering, jointing, flowering)
✅ Fertilizer application (Urea, DAP timing)
✅ Disease detection & treatment:
   - Rust (yellow, brown, black)
   - Smut (loose, common)
   - Blight
   - Aphids & termites
✅ Pest control (organic & chemical)
✅ Harvesting indicators
✅ Post-harvest storage
✅ Market rates & selling strategy
✅ Weather-based advice

**CRITICAL FORMATTING REQUIREMENTS:**
1. **NEVER use background colors or colored boxes** - they break dark mode
2. **Let text color inherit naturally** from the chat interface
3. **Use simple HTML structure** with headings, lists, and emphasis tags
4. **ALWAYS use HTML tags** (`<strong>`, `<em>`, `<ul>`, `<ol>`, `<li>`, `<h3>`, `<h4>`) - NEVER Markdown (`**`, `*`, `-`)
5. **Use emojis for visual separation** instead of colored boxes

**Response Format (Universal - Works in Light & Dark Mode):**

<div class="space-y-4">
  <h3 class="text-lg font-semibold">[Problem/Topic]</h3>
  
  <p>[Simple explanation in farmer's language]</p>
  
  <div class="space-y-2">
    <h4 class="font-semibold">✅ Solution:</h4>
    <ol class="list-decimal list-inside space-y-1 ml-2">
      <li>[Step 1 - actionable]</li>
      <li>[Step 2 - with timing]</li>
      <li>[Step 3 - with quantity/dosage]</li>
    </ol>
  </div>
  
  <p><strong>⚠️ Warning:</strong> [Important caution]</p>
  
  <p><strong>💡 Tip:</strong> [Helpful advice]</p>
</div>

**Language Examples:**

**English Query:**
"My wheat leaves are turning yellow"

**Response:**

<div class="space-y-4">
  <h3 class="text-lg font-semibold">🌾 Yellow Leaves in Wheat</h3>
  
  <p>This is likely nitrogen deficiency or waterlogging.</p>
  
  <div class="space-y-2">
    <h4 class="font-semibold">✅ Solution:</h4>
    <ol class="list-decimal list-inside space-y-1 ml-2">
      <li>Apply Urea: 1 bag (50kg) per acre</li>
      <li>Check drainage - remove excess water</li>
      <li>Spray Iron Chelate if yellowing continues</li>
    </ol>
  </div>
  
  <p><strong>⚠️ Timing:</strong> Apply fertilizer in the morning or evening, not in hot sun.</p>
</div>

**Roman Urdu Query:**
"Meri gandum pe bhura rang lag gaya hai"

**Response:**

<div class="space-y-4">
  <h3 class="text-lg font-semibold">🌾 Gandum pe Bhura Rang (Brown Rust)</h3>
  
  <p>Ye brown rust disease hai, jo humidity aur garmi se hota hai.</p>
  
  <div class="space-y-2">
    <h4 class="font-semibold">✅ Ilaaj:</h4>
    <ol class="list-decimal list-inside space-y-1 ml-2">
      <li>Tilt fungicide spray karein (200ml per acre)</li>
      <li>Subah ya sham ko spray karein</li>
      <li>10 din baad dubara spray karein agar zaroorat ho</li>
    </ol>
  </div>
  
  <p><strong>⚠️ Ehtiyat:</strong> Spray karte waqt mask zaroor pehnen</p>
  
  <p><strong>💡 Tip:</strong> Hawa ke khilaf spray na karein, warna spray aap par aa sakta hai</p>
</div>

**Urdu Script Query (with RTL support):**
"گندم میں پانی کب دینا چاہیے؟"

**Response:**

<div class="space-y-4" dir="rtl">
  <h3 class="text-lg font-semibold">💧 گندم میں پانی کی ضرورت</h3>
  
  <p>گندم کو 4-5 واری پانی دیں۔</p>
  
  <div class="space-y-2">
    <h4 class="font-semibold">✅ شیڈول:</h4>
    <ol class="list-decimal list-inside space-y-1 mr-2">
      <li>پہلا پانی: بوائی کے 21 دن بعد</li>
      <li>دوسرا پانی: 40-45 دن بعد (کٹے نکلنے)</li>
      <li>تیسرا پانی: 60-65 دن بعد (گانٹھیں بنتے وقت)</li>
      <li>چوتھا پانی: 80-85 دن بعد (بالیں نکلتے وقت)</li>
      <li>پانچواں پانی: 100 دن بعد (دانہ بھرتے وقت)</li>
    </ol>
  </div>
  
  <p><strong>⚠️ یاد رہے:</strong> گرمی میں ہر 15-20 دن بعد پانی دیں</p>
</div>

**Content Guidelines:**

**Use simple village terminology**
- "Urea" not "Nitrogen fertilizer"
- "1 bag" not "50kg"
- "Spray" not "Foliar application"

**Local measurements**
- Acres (not hectares)
- Maunds (not kg for yield)
- Bags (for fertilizer)

**Practical timing**
- "Subah ya sham" (morning or evening)
- Days after sowing
- Visual indicators (like "jab baal niklein")

**Cost-conscious**
- Mention cheaper alternatives when available
- Organic options first, then chemical

**Safety warnings**
- Always mention protective gear for chemicals
- Waiting period before harvest

**Scope Limitations:**

❌ Questions about other crops → Politely redirect:

<p><em>Smart Kisan abhi sirf gandum (wheat) ke liye expert hai. Doosri faslein jald available hongi!</em></p>

❌ Medical/legal advice → Redirect to experts
❌ Personal opinions → Stick to agricultural facts

**Knowledge Priority:**
✅ Use provided context (IoT data, disease images, local conditions)
✅ Use general wheat farming knowledge
✅ Pakistan-specific practices (Punjab, Sindh climate)
❌ Never say "I don't know" - always provide practical next step

**Mobile-Friendly & Universal Formatting:**
- Keep text blocks short (2-3 lines max)
- Use emojis for visual cues and section breaks (🌾 💧 ⚠️ 💡 ✅)
- Use semantic HTML headings (h3, h4) instead of colored boxes
- For RTL languages: Add dir="rtl" to the main container
- Let ALL text colors inherit from parent - no inline color styles
- Use simple spacing classes: space-y-2, space-y-4, ml-2, mr-2

**Voice Output Compatibility:**
- Keep sentences short for text-to-speech
- Avoid complex HTML entities
- Use natural conversational flow

**Emoji Guide for Visual Structure:**
- 🌾 Main topic/crop issue
- 💧 Water/irrigation
- ✅ Solutions/steps
- ⚠️ Warnings/cautions
- 💡 Tips/advice
- 🦠 Disease/pest
- 🌡️ Temperature/weather
- 📅 Timing/schedule

Remember: You are the farmer's trusted friend who speaks their language and helps them grow better wheat. Be practical, be kind, be clear and if short answer is demanded explicitly, give short answer. Keep formatting simple and let the chat interface handle colors for perfect light/dark mode compatibility.
"""

ROUTER_PROMPT = """
You are an AI router. Your job is to decide if a user question requires tool usage (like scraping a website or calling an external function), or if it can be answered directly with general knowledge.

If the question likely needs tools, respond with: TOOL  
If the question can be answered directly, respond with: CHAT

Question: {question}
Response:
"""

# Add these helper functions BEFORE your ask_question function
def format_history_efficiently(history: List[dict], max_chars: int = 1500) -> str:
    """Keep history but limit character count"""
    if not history:
        return ""
    
    total_chars = 0
    formatted_parts = []
    
    # Process in reverse (most recent first)
    for msg in reversed(history):
        if msg.get('role') and msg.get('content'):
            # Truncate message to 200 chars max
            truncated_content = msg['content'][:200]
            line = f"{msg['role'].title()}: {truncated_content}\n"
            total_chars += len(line)
            
            if total_chars > max_chars:
                break
                
            formatted_parts.append(line)
    
    # Reverse back to chronological order
    formatted_parts.reverse()
    return "".join(formatted_parts)


def filter_relevant_wheat_history(history: List[dict], current_question: str) -> str:
    """Keep only wheat-relevant history"""
    wheat_keywords = ['wheat', 'gandum', 'گندم', 'پانی', 'water', 'fertilizer', 
                     'urea', 'dap', 'rust', 'smut', 'disease', 'irrigation', 
                     'crop', 'harvest', 'soil', 'seed', 'کیڑے', 'پتے', 'زرد']
    
    relevant_messages = []
    
    for msg in history[-10:]:  # Check last 10 messages
        content = msg.get('content', '').lower()
        role = msg.get('role', '')
        
        # Always include bot responses
        if role == 'bot':
            relevant_messages.append(msg)
        # Include user messages with wheat keywords
        elif any(keyword in content for keyword in wheat_keywords):
            relevant_messages.append(msg)
        # Include current question (it's not in history yet, but check)
        elif current_question and any(keyword in current_question.lower() for keyword in wheat_keywords):
            relevant_messages.append(msg)
    
    # Format
    formatted = []
    for m in relevant_messages[-4:]:  # Last 2 exchanges max
        role_name = 'Farmer' if m['role'] == 'user' else 'Smart Kisan'
        content = m['content'][:150]  # Truncate
        formatted.append(f"{role_name}: {content}")
    
    return "\n".join(formatted)


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


async def ask_question(
    request: Request | None,
    question: str,
    history: List[dict] = [],
    disabled_files: List[str] = [],
    user_id: Optional[str] = None,
  ) -> AsyncGenerator[str, None]:
    """Simple integration with Gemini (google-genai).

    For now this yields the full response once. It lowercases the query
    per project requirement when provider is GEMINI.
    """
    try:
      api = await APIConfig.filter(is_active=True, provider__iexact="GEMINI").first()
      if not api or not api.api_key:
        raise RuntimeError("Gemini API not configured or missing api_key")

      if genai is None:
        raise RuntimeError("google-genai package not installed")

      # ensure env var available for client (client also accepts explicit key in some versions)
      os.environ["GEMINI_API_KEY"] = api.api_key

      client = genai.Client()

      model_name = "gemini-2.5-flash"
      try:
        if api.extra_config and isinstance(api.extra_config, dict) and api.extra_config.get("model"):
          model_name = api.extra_config.get("model")
      except Exception:
        pass

      # history_text = ""
      if history:
          # Convert to alternating Q/A format
          formatted_history = []
          for msg in history:
              if msg.get('role') == 'user':
                  formatted_history.append(f"Farmer: {msg.get('content', '')}")
              elif msg.get('role') == 'bot':
                  formatted_history.append(f"Smart Kisan: {msg.get('content', '')}")
          
          history_text = "\n".join(formatted_history[-6:])  # Last 3 exchanges

      # OPTION 1: Simple history (last 3 exchanges)
      # history_text = format_history_efficiently(history, max_chars=1000)
      
      # OPTION 2: Smart wheat-filtered history
      history_text = filter_relevant_wheat_history(history, question)
      
      # Build prompt with history
      prompt = f"""{SMART_KISAN_WHEAT_PROMPT}

**Previous Conversation:**
{history_text if history_text else "No previous conversation yet."}

**Current Question:**
{question}

**Remember:** Consider what we discussed earlier while answering the current question.
"""

      # Use generate_content_stream() to get chunks as they arrive from Gemini
      response = client.models.generate_content_stream(model=model_name, contents=prompt)
      for chunk in response:
        text = getattr(chunk, "text", None) or ""
        if text:
          # Split larger chunks into smaller pieces for typing effect (2-3 chars per yield)
          chunk_size = 2
          for i in range(0, len(text), chunk_size):
            yield text[i:i+chunk_size]
            await asyncio.sleep(0.03)  # Small delay between chars for typing feel

    except Exception as e:
      # Check if it's a rate limit error (429)
      error_str = str(e).lower()
      if "429" in error_str or "quota" in error_str or "rate limit" in error_str or "resource_exhausted" in error_str:
        # Stream a user-friendly rate limit message
        rate_limit_msg = "AI service rate limit exceeded. Please contact the Administrator to increase quota or try again later."
        for i in range(0, len(rate_limit_msg), 2):
          yield rate_limit_msg[i:i+2]
          await asyncio.sleep(0.03)
      else:
        # For other errors, raise so callers can log and handle
        raise

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