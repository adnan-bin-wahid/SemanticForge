from sentence_transformers import SentenceTransformer

# Load a lightweight model for code embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for a given text (code snippet).
    
    Args:
        text: The code snippet or description to embed
        
    Returns:
        A list of floats representing the embedding vector
    """
    embedding = model.encode(text, convert_to_tensor=False)
    return embedding.tolist()
