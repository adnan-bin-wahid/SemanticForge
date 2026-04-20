from app.services.context_retriever import ContextRetriever
from app.services.llm_client import OllamaClient


class CodeGenerator:
    """
    Service orchestrating code generation through context retrieval and LLM inference.
    
    Workflow:
    1. Retrieve relevant context from the codebase based on user instruction
    2. Format context into a structured prompt template
    3. Send prompt to Ollama LLM service via OllamaClient
    4. Return generated code and formatting details
    """
    
    def __init__(self, context_retriever: ContextRetriever, ollama_base_url: str, model: str = "tinyllama"):
        """
        Initialize the CodeGenerator service.
        
        Args:
            context_retriever (ContextRetriever): Service for retrieving code context
            ollama_base_url (str): Base URL of the Ollama service
            model (str): LLM model to use (default: "tinyllama")
        """
        self.context_retriever = context_retriever
        self.llm_client = OllamaClient(base_url=ollama_base_url, model=model)

    async def generate_code(
        self,
        user_instruction: str,
        limit: int = 10,
        temperature: float = 0.7
    ) -> dict:
        """
        Generate code based on a user instruction using hybrid context retrieval and LLM.
        
        Args:
            user_instruction (str): Natural language instruction for code generation
            limit (int): Maximum number of context symbols to retrieve (default: 10)
            temperature (float): LLM sampling temperature, 0.0-1.0 (default: 0.7)
        
        Returns:
            dict: Contains:
                - generated_code: The raw code string from the LLM
                - prompt: The structured prompt that was sent to the LLM
        
        Raises:
            Exception: From context retrieval or LLM client if errors occur
        """
        # 1. Retrieve relevant context from codebase
        context = await self.context_retriever.retrieve_context(user_instruction, limit)

        # 2. Format context into structured prompt template
        prompt = self._format_prompt(user_instruction, context)

        # 3. Call LLM via Ollama client
        generated_code = await self.llm_client.generate(
            prompt=prompt,
            temperature=temperature
        )
        
        return {
            "generated_code": generated_code,
            "prompt": prompt
        }

    def _format_prompt(self, instruction: str, context: dict) -> str:
        """
        Generate a sophisticated, structured prompt template for the LLM.
        The template incorporates the user's instruction and relevant codebase context
        to guide code generation with awareness of existing patterns and structure.
        """
        prompt = "# Code Generation Task\n\n"
        
        # Section 1: User's Instruction
        prompt += "## User Request\n"
        prompt += f"Generate code to accomplish the following:\n\n**{instruction}**\n\n"
        
        # Section 2: Relevant Code Examples from Repository
        prompt += "## Relevant Code Context from the Repository\n"
        prompt += "The following symbols are relevant to your task:\n\n"
        
        search_results = context.get("search_results", [])
        if search_results:
            for i, result in enumerate(search_results, 1):
                confidence = "High" if result.score > 0.7 else "Medium" if result.score > 0.4 else "Low"
                prompt += f"{i}. **{result.name}** (Relevance: {confidence}, Score: {result.score:.4f})\n"
                if result.docstring:
                    prompt += f"   - Docstring: {result.docstring}\n"
        else:
            prompt += "No specific context symbols found.\n"
            
        prompt += "\n"
        
        # Section 3: Code Structure and Examples
        prompt += "## Codebase Structure and Related Code\n"
        prompt += "Below are existing code patterns in the repository that you should follow:\n\n"
        
        expanded_context = context.get("expanded_context", {})
        if expanded_context:
            for symbol, data in expanded_context.items():
                prompt += f"### {symbol}\n"
                prompt += f"**Location:** `{data.get('path', 'unknown')}`\n"
                
                if data.get('code'):
                    prompt += f"\n**Implementation:**\n```python\n{data['code']}\n```\n"
                
                neighbors = data.get("neighbors", {})
                if neighbors:
                    prompt += f"\n**Related Symbols:**\n"
                    for neighbor, neighbor_info in neighbors.items():
                        rel_type = neighbor_info.get('type', 'related')
                        prompt += f"- `{neighbor}` ({rel_type}) at `{neighbor_info.get('path')}`\n"
                
                prompt += "\n"
        else:
            prompt += "No existing code structure found.\n\n"
        
        # Section 4: Generation Guidelines
        prompt += "## Code Generation Guidelines\n"
        prompt += """Please generate Python code following these requirements:
1. **Compatibility:** Ensure the generated code integrates seamlessly with the existing codebase.
2. **Style:** Match the coding style and conventions observed in the examples above.
3. **Structure:** Follow the module structure and patterns established in the repository.
4. **Clarity:** Write clear, well-commented code with meaningful variable and function names.
5. **Best Practices:** Use Python best practices including error handling, type hints (if used in the codebase), and docstrings.
6. **No Duplication:** Avoid reimplementing functionality that already exists in the codebase.

## Your Response
Generate the solution code below. Include only the Python code without explanations or markdown formatting:
"""
        return prompt
