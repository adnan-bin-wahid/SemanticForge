import httpx
from app.services.context_retriever import ContextRetriever

class CodeGenerator:
    def __init__(self, context_retriever: ContextRetriever, ollama_base_url: str):
        self.context_retriever = context_retriever
        self.ollama_base_url = ollama_base_url.rstrip('/')
        self.client = httpx.AsyncClient()

    async def generate_code(self, user_instruction: str, limit: int = 10):
        # 1. Retrieve context
        context = await self.context_retriever.retrieve_context(user_instruction, limit)

        # 2. Format the prompt
        prompt = self._format_prompt(user_instruction, context)

        # 3. Call Ollama
        response = await self.client.post(
            f"{self.ollama_base_url}/api/generate",
            json={
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False
            },
            timeout=60.0
        )
        response.raise_for_status()
        
        generated_code = response.json().get("response", "")
        
        return {"generated_code": generated_code, "prompt": prompt}

    def _format_prompt(self, instruction: str, context: dict) -> str:
        # This is a simple example. You can create a much more sophisticated prompt.
        prompt = f"Instruction: {instruction}\n\n"
        prompt += "Here is some relevant context from the codebase:\n\n"

        for result in context.get("search_results", []):
            prompt += f"## Search Result: {result.name} (Score: {result.score})\n"
            
        prompt += "\n## Expanded Context (Code Neighbors):\n"
        for symbol, data in context.get("expanded_context", {}).items():
            prompt += f"### Context for `{symbol}` (Path: {data.get('path')})\n"
            if data.get('code'):
                prompt += f"```python\n{data['code']}\n```\n"
            for neighbor, neighbor_info in data.get("neighbors", {}).items():
                prompt += f"- Neighbor `{neighbor}` ({neighbor_info.get('type')}) at `{neighbor_info.get('path')}`\n"
        
        prompt += "\nBased on the instruction and the context, generate the Python code to fulfill the request."
        return prompt
