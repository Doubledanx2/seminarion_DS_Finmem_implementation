import os
import numpy as np
from typing import List, Union


class LocalSentenceTransformerEmb:
    """Local GPU embedding backend (ARCHITECTURE.md deviation D-emb: bge-large-en-v1.5
    on the RTX 3090 instead of ada-002; dim 1024 vs 1536). Same interface as
    OpenAILongerThanContextEmb so memorydb.py is agnostic to the backend."""

    def __init__(
        self,
        embedding_model: str = "BAAI/bge-large-en-v1.5",
        chunk_size: int = 5000,  # accepted for config compatibility; unused
        verbose: bool = False,
        device: Union[str, None] = None,
    ) -> None:
        import torch
        from sentence_transformers import SentenceTransformer

        self.model_name = embedding_model
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SentenceTransformer(embedding_model, device=self.device)
        self.verbose = verbose

    def __call__(self, text: Union[List[str], str]) -> np.ndarray:
        if isinstance(text, str):
            text = [text]
        emb = self.model.encode(
            text, show_progress_bar=self.verbose, convert_to_numpy=True, batch_size=32
        )
        return np.asarray(emb, dtype="float32")

    def get_embedding_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()


def make_embedding_function(**emb_config):
    """Factory used by memorydb.BrainDB. Select with `backend = "local" | "openai"`
    in [agent.agent_1.embedding.detail]; defaults to the paper's OpenAI path."""
    config = dict(emb_config)
    backend = config.pop("backend", "openai")
    if backend == "local":
        return LocalSentenceTransformerEmb(**config)
    return OpenAILongerThanContextEmb(**config)


class OpenAILongerThanContextEmb:
    """
    Embedding function with openai as embedding backend.
    If the input is larger than the context size, the input is split into chunks of size `chunk_size` and embedded separately.
    The final embedding is the average of the embeddings of the chunks.
    Details see: https://github.com/openai/openai-cookbook/blob/main/examples/Embedding_long_inputs.ipynb
    """

    def __init__(
        self,
        openai_api_key: Union[str, None] = None,
        embedding_model: str = "text-embedding-ada-002",
        chunk_size: int = 5000,
        verbose: bool = False,
    ) -> None:
        """
        Initializes the Embedding object.

        Args:
            openai_api_key (str): The API key for OpenAI.
            embedding_model (str, optional): The model to use for embedding. Defaults to "text-embedding-ada-002".
            chunk_size (int, optional): The maximum number of token to send to openai embedding model at one time. Defaults to 5000.
            verbose (bool, optional): Whether to show progress bar during embedding. Defaults to False.

        Returns:
            None
        """
        # lazy import: only the ada-002 backend needs langchain_community
        from langchain_community.embeddings import OpenAIEmbeddings

        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.emb_model = OpenAIEmbeddings(
            model=embedding_model,
            api_key=openai_api_key or os.environ.get("OPENAI_API_KEY"),
            chunk_size=chunk_size,
            show_progress_bar=verbose,
        )

    def _emb(self, text: Union[List[str], str]) -> List[List[float]]:
        """
        Asynchronously performs embedding on a list of text.

        This method calls the `aembed_documents` method of the `emb_model` object to embed the input text.

        Args:
            self: The instance of the class.
            text (List[str]): A list of text to be embedded.

        Returns:
            List[List[float]]: The embeddings of the input text as a list of lists of floats.

        """
        if isinstance(text, str):
            text = [text]
        return self.emb_model.embed_documents(texts=text, chunk_size=None)

    def __call__(self, text: Union[List[str], str]) -> np.ndarray:
        """
        Performs embedding on a list of text.

        This method calls the `_emb` method to asynchronously embed the input text using the `emb_model` object.

        Args:
            self: The instance of the class.
            text (List[str]): A list of text to be embedded.

        Returns:
            np.array: The embedding of the input text as a NumPy array.

        """
        return np.array(self._emb(text)).astype("float32")

    def get_embedding_dimension(self):
        """
        Returns the dimension of the embedding.

        This method checks the value of `self.emb_model.model` and returns the corresponding embedding dimension. If the model is not implemented, a `NotImplementedError` is raised.

        Args:
            self: The instance of the class.

        Returns:
            int: The dimension of the embedding.

        Raises:
            NotImplementedError: Raised when the embedding dimension for the specified model is not implemented.

        """
        match self.emb_model.model:
            case "text-embedding-ada-002":
                return 1536
            case _:
                raise NotImplementedError(
                    f"Embedding dimension for model {self.emb_model.model} not implemented"
                )
