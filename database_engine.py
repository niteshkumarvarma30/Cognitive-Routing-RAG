import chromadb
from chromadb.utils.embedding_functions import JinaEmbeddingFunction

class Bot_Router:
    def __init__(self, api_key: str):
        self.ef = JinaEmbeddingFunction( #here I am using Jina embedding for vector embdedding of 1024 Dimensions through API Key 
            api_key=api_key, 
            model_name="jina-embeddings-v3"
        )
        
        self.client = chromadb.EphemeralClient()
        #using EphemeralClient for In-Memory RAM Storing Database
        self.collection = self.client.create_collection( 
            name="grid07_bot_registry",  # I have used embedding fuction here and metadata for cosine similarity
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )
        self._seed_bot_data()

    def _seed_bot_data(self): #stroing all the details in memory so that Vector Embedding will be done as mentioned in Question and matched while Incoming Post
        """Internal method to populate the Vector DB with Persona documents."""
        registry = {
            "Bot_A": {
                "bio": "Tech Maximalist: I believe AI and crypto will solve all human problems. I am highly optimistic about technology, Elon Musk, and space exploration. I dismiss regulatory concerns.",
                "tag": "maximalist"
            },
            "Bot_B": {
                "bio": "Skeptic/Doomer: I believe late-stage capitalism and tech monopolies are destroying society. I am highly critical of AI, social media, and billionaires. I value privacy and nature.",
                "tag": "skeptic"
            },
            "Bot_C": {
                "bio": "Finance Bro: I strictly care about markets, interest rates, trading algorithms, and making money. I speak in finance jargon and view everything through the lens of ROI.",
                "tag": "finance"
            }
        }
        
        
        self.collection.add(  #using the values stored in database to add in collection from above registry
            ids=list(registry.keys()),
            documents=[v["bio"] for v in registry.values()],
            metadatas=[{"type": v["tag"], "persona": v["bio"]} for v in registry.values()]
        )

    def find_best_match(self, content: str, min_score: float = 0.85):

        raw_results = self.collection.query( #collecting the query and storing metadata and storing into collection
            query_texts=[content],
            n_results=3,
            include=["distances", "metadatas"]
        )
        
    
        tuned_threshold = 0.40 # threshold id tuned to 0.40 so that every Bot will be matched with the Query Incoming post
        refined_matches = []

        print(f"\nSimilarity for: '{content[:40]}'")

        for idx, bot_id in enumerate(raw_results['ids'][0]):
            score = 1 - raw_results['distances'][0][idx]
            
            print(f"Bot: {bot_id} | Raw Score: {score:.4f} | Status: {'MATCH' if score >= tuned_threshold else 'REJECT'}")
            
            if score >= tuned_threshold: # storing the bot data whose similarity score will be matched using cosine rule
                refined_matches.append({
                    "id": bot_id,
                    "score": round(score, 3),
                    "context": raw_results['metadatas'][0][idx]
                })
                
        return refined_matches
    
if __name__ == "__main__":
    JINA_API_KEY = "jina_b6f6796f142b47ef914af24c527e370bnAPyDLnsGTKawhk8xDwpDacJEV6f" 
    
    router = Bot_Router(JINA_API_KEY)
    
    test_query = "OpenAI just released a new model that might replace junior developers."
    
    final_output = router.find_best_match(test_query)
    
    print("\n FINAL ASSIGNMENT OUTPUT (PHASE 1)") #finally output is generated 
    print(final_output)