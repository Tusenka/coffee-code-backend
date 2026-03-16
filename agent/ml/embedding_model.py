from uuid import UUID

from sentence_transformers import SentenceTransformer

from agent.metrics.utils import perf


class EmbeddingModel:
    def __init__(self, model_name="intfloat/multilingual-e5-base"):
        self.model = SentenceTransformer(model_name)

    @perf("generate_embeddings")
    def generate_embeddings(self, bios: list[str], ids: list[UUID]):
        for i, b in enumerate(bios):
            assert b, f"Bio for {ids[i]} is empty"
        return zip(ids, self.model.encode(bios, normalize_embeddings=True))
